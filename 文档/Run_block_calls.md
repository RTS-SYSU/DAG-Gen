# `FixedwingRateControl::Run()` 关键分支与相关调用映射

汇总 `Run()` 中两个关键片段在 `dag.dot` 内的调用链，并标注非源码显式调用的来源，便于与 `FixedwingRateControl.cpp` 对照。

## A. `should_exit()` 分支（早退清理）

源码：
```cpp
if (should_exit()) {
    _vehicle_angular_velocity_sub.unregisterCallback();
    exit_and_cleanup();
    return;
}
```

dot 对应调用：
- `FixedwingRateControl::Run()` → `uORB::Manager::unregister_callback(void*, uORB::SubscriptionCallback*)1`  
  来源：`_vehicle_angular_velocity_sub.unregisterCallback()` 内联封装调用 uORB 管理器注销回调。
- `uORB::Manager::unregister_callback(void*, uORB::SubscriptionCallback*)1` → `pthread_mutex_lock2`  
  非源码：uORB 管理器内部加锁。
- `pthread_mutex_lock2` → `FixedwingRateControl::~FixedwingRateControl()`  
  来源：`exit_and_cleanup()` 路径触发对象销毁。
- `FixedwingRateControl::~FixedwingRateControl()` → `operator delete(void*, unsigned long)4` → `pthread_mutex_unlock5`  
  非源码：默认删除运算符与解锁，属于析构/清理流程。

说明：`exit_and_cleanup()` 本身未单独现身 dot，调用被归入析构链。节点后缀数字为编译器标记调用点，不对应源码行号。

## B. 参数更新与角速度采样片段

源码节选：
```cpp
bool params_updated = _parameter_update_sub.updated();
if (params_updated) {
    parameter_update_s pupdate;
    _parameter_update_sub.copy(&pupdate);
    updateParams();
    parameters_update();
}
float dt = 0.f;
static constexpr float DT_MIN = 0.002f;
static constexpr float DT_MAX = 0.04f;
vehicle_angular_velocity_s vehicle_angular_velocity{};
if (_vehicle_angular_velocity_sub.copy(&vehicle_angular_velocity)) {
    dt = math::constrain((vehicle_angular_velocity.timestamp_sample - _last_run) * 1e-6f, DT_MIN, DT_MAX);
    _last_run = vehicle_angular_velocity.timestamp_sample;
}
if (dt < DT_MIN || dt > DT_MAX) {
    const hrt_abstime time_now_us = hrt_absolute_time();
    dt = math::constrain((time_now_us - _last_run) * 1e-6f, DT_MIN, DT_MAX);
    _last_run = time_now_us;
}
vehicle_angular_velocity_s angular_velocity{};
_vehicle_angular_velocity_sub.copy(&angular_velocity);
Vector3f rates(angular_velocity.xyz);
Vector3f angular_accel{angular_velocity.xyz_derivative};
```

dot 对应调用（主要来自 `Run().part.0` 展开）：
- `FixedwingRateControl::Run().part.0` → `uORB::SubscriptionInterval::updated()` ×2  
  来源：`_parameter_update_sub.updated()` 内联，内部调用 uORB 管理器检查更新。
- `FixedwingRateControl::Run().part.0` → `hrt_absolute_time`  
  非源码：`SubscriptionInterval::updated()` 内部以及 dt 回退分支使用的时间戳获取。
- `FixedwingRateControl::Run().part.0` → `uORB::SubscriptionInterval::copy(void*)` ×多次  
  来源：`_parameter_update_sub.copy(&pupdate)` 内联，内部调用 uORB 管理器复制数据。
- `FixedwingRateControl::Run().part.0/uORB::Subscription::subscribe()` ↔ `uORB::Manager::orb_data_copy(...)`  
  非源码：`SubscriptionInterval::copy` 内部为确保订阅注册/读取底层队列而调用，源文件未显式写出。
- `FixedwingRateControl::Run().part.0/non-virtual thunk to FixedwingRateControl::updateParamsImpl()`  
  来源：`updateParams()`（ModuleParams 提供的虚函数）被调用，编译器生成非虚表 thunks。
- `FixedwingRateControl::parameters_update()`  
  源码显式调用，紧随 `updateParams()`。
- `_vehicle_angular_velocity_sub.copy(...)` 对应：`uORB::Subscription::subscribe()` / `uORB::Manager::orb_data_copy(...)` 再次出现  
  非源码：copy 内联封装自动确保订阅有效并读取样本。
- 回退 dt 分支：`hrt_absolute_time` 再次出现（获取当前时间）。

说明：
- uORB 相关的 `subscribe`/`orb_data_copy` 等均来自订阅封装的内联逻辑，不在 `.cpp` 明写。
- `updateParams()` 的调用在 dot 中标记为 “non-virtual thunk …” 属于编译器生成的适配符号。
- 该片段没有额外的线程/锁调用，主要是 uORB 管理器与时间戳函数作为“非源码显式”调用出现在 dot。
   


这些重复的链条来自 ModuleParams/DEFINE_PARAMETERS 宏在构造函数里为每一个参数句柄做的同样模板化调用。对每个参数，生成的代码都会按固定顺序调用：

param_name 取名字，用于日志输出。
px4_log_modulename 获取模块名前缀（PX4_ERR 用）。
param_get 读当前值。
param_set_used、param_type 等辅助接口记录/校验类型。
由于 FixedwingRateControl 定义了大量参数，构造函数里内联展开后，你会看到这段 “param_name → px4_log_modulename → param_get → param_set_used → param_type → …” 的模式按顺序重复多次，每次对应一个不同的参数句柄。因此在 expand/dot 中出现成组的相似边，并非代码重复，而是宏展开后为每个参数都生成了一套一致的初始化/检查调用。


这些重复的订阅/反订阅链条同样源于构造函数中多个 uORB 订阅成员的初始化/清理被内联展开。FixedwingRateControl 有一系列订阅成员（如 _vehicle_angular_velocity_sub、_battery_status_sub、_manual_control_setpoint_sub、_rates_sp_sub、_vehicle_control_mode_sub 等），每个都是 uORB::Subscription 或 SubscriptionCallbackWorkItem 类型。它们的构造函数会：

调用 Subscription::subscribe() 多次以确保注册、设置队列、可能重试不同实例；
在异常处理或清理路径调用 unsubscribe()，再回到下一次尝试。
因为每个成员都会生成相似的内部调用序列，编译展开后在 .expand/dot 中就出现了多组连续的 subscribe() 调用，偶尔夹杂 unsubscribe()（对应某次尝试失败或析构清理）。数字后缀只是不同调用点的标签，表明这些调用对应不同的订阅成员或同一成员的不同内部步骤。

简而言之：多个订阅成员的构造/清理逻辑被内联，且每个都会进行一套标准的 subscribe/unsubscribe 流程，导致在 dot 文件里出现多段几乎相同的 Subscription::subscribe() 链。