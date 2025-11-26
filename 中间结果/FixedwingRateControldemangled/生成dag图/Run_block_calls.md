# `FixedwingRateControl::Run()` 源码与 `dag.dot` 调用映射（源码/非源码完整对照）

面向整段 `Run()`，按执行顺序列出源码操作及在 `dag.dot` 中出现的调用（包含内联、框架、编译器插桩）。节点名后缀数字是调用点标签，不对应源码行号。

## A. 早退清理
- 源码：`should_exit()` → `_vehicle_angular_velocity_sub.unregisterCallback()` → `exit_and_cleanup()` → `return;`
- dot：`FixedwingRateControl::Run()` → `uORB::Manager::unregister_callback` → `pthread_mutex_lock` → `FixedwingRateControl::~FixedwingRateControl` → `operator delete` → `pthread_mutex_unlock`（unregisterCallback 内联 + exit_and_cleanup 析构链）

## B. 性能计数开始
- 源码：`perf_begin(_loop_perf);`
- dot：`Run().part.0/perf_begin1`（性能计数插桩）

## C. 控制触发判断与参数更新
- 源码：`_vehicle_angular_velocity_sub.updated() || hrt_elapsed_time(&_last_run) > 20_ms`
- 源码：参数块 `_parameter_update_sub.updated()` → `copy(&pupdate)` → `updateParams()` → `parameters_update()`
- dot（非源码）：`uORB::SubscriptionInterval::updated()`、`uORB::SubscriptionInterval::copy(void*)`、`uORB::Subscription::subscribe()`、`uORB::Manager::orb_data_copy(...)`、`hrt_absolute_time`、`non-virtual thunk to FixedwingRateControl::updateParamsImpl()`、`FixedwingRateControl::parameters_update()`

## D. dt 计算与角速度采样
- 源码：`_vehicle_angular_velocity_sub.copy(&vehicle_angular_velocity)`；若 dt 越界则用 `hrt_absolute_time()` 回退；再 copy 到 `angular_velocity`。
- dot（非源码）：`uORB::Subscription::subscribe()` / `uORB::Manager::orb_data_copy(...)`（两次 copy 内联）；`hrt_absolute_time`（回退 dt 分支）

## E. 尾座旋翼帧转换
- 源码：tailsitter 时重排 `rates`/`angular_accel`。
- dot：无额外非源码调用（纯数学运算）

## F. 状态与模式轮询、旋翼早退
- 源码：`_vehicle_status_sub.update`、`_vehicle_control_mode_sub.update`、`vehicle_land_detected_poll()`、`vehicle_manual_poll()`；旋翼模式时 `perf_end` 后 return。
- dot（非源码）：`uORB::Subscription::subscribe` / `uORB::Manager::updates_available` / `orb_data_copy`（两次 poll 内联）；`get_orb_meta` / `orb_advertise` / `uORB::Manager::orb_publish` / `hrt_absolute_time`（manual poll 发布 rates_sp）；`__stack_chk_fail`（poll 尾部栈保护）

## G. 速率控制主路径（flag_control_rates_enabled）
- 源码：空速缩放、积分重置、饱和反馈、配平插值、读取 rate setpoint、前馈、PID、Acro 偏航特例、电池补偿、状态发布。
- dot（非源码）：`uORB::Subscription::subscribe` / `orb_data_copy`（control_allocator_status、rates_sp、battery_status）；`uORB::SubscriptionInterval::updated/copy`（rates_sp）；`uORB::Manager::orb_publish` / `get_orb_meta` / `hrt_absolute_time`（rate_ctrl_status 发布）
- 源码显式：`interpolate`、`resetIntegral`、`_rate_control.update`、`matrix::constrain`、配平与前馈设定等。

## H. 输出调整与推力/扭矩发布
- 源码：横滚→偏航前馈；tailsitter 输出变换；条件发布 thrust/torque setpoint（附时间戳）。
- dot（非源码）：`uORB::Manager::orb_publish` / `get_orb_meta` / `orb_advertise`（publish 封装）；`hrt_absolute_time`（打时间戳）

## I. 能量统计与手动襟翼/扰流板
- 源码：`updateActuatorControlsStatus(dt)`；手动 flaps/spoilers publish。
- dot（非源码）：`uORB::Manager::orb_publish` / `get_orb_meta`、`hrt_absolute_time`（两处 publish 内联）

## J. 调度与性能计数结束
- 源码：`ScheduleDelayed(20_ms);`、`perf_end(_loop_perf);`
- dot：`perf_end` 插桩；调度本身未单列，相关队列调用可在 `px4::WorkQueue::Add`（由回调机制触发的节点）看到。
