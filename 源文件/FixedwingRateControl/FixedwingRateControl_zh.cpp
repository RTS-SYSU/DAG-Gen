/****************************************************************************
 *
 *   Copyright (c) 2013-2023 PX4 Development Team. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 * 3. Neither the name PX4 nor the names of its contributors may be
 *    used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 * OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
 * AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 * ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 ****************************************************************************/

// 下面是对原始文件 FixedwingRateControl.cpp 的完整中文逐行注释版本
// 文件名：FixedwingRateControl_zh.cpp
// 说明：保持原始实现不变，但在每个重要语句或每行附近加入中文注释，帮助初学者理解

#include "FixedwingRateControl.hpp" // 引入对应的头文件，声明类 FixedwingRateControl 的成员和依赖

using namespace time_literals; // 使用 time_literals 命名空间，允许写类似 1_s 的时间字面量
using namespace matrix; // 使用 matrix 命名空间，便于直接使用 Vector3f 等矩阵/向量类型

using math::constrain; // 引入 math 命名空间中的 constrain（约束）函数到当前作用域
using math::interpolate; // 引入插值函数
using math::radians; // 引入角度转弧度函数

// 构造函数：FixedwingRateControl(bool vtol)
// 参数 vtol：指示是否为 VTOL（垂直起降）相关的控制器变体
FixedwingRateControl::FixedwingRateControl(bool vtol) :
	ModuleParams(nullptr), // 初始化 ModuleParams 基类（参数管理）
	ScheduledWorkItem(MODULE_NAME, px4::wq_configurations::nav_and_controllers), // 指定调度队列
	_actuator_controls_status_pub(vtol ? ORB_ID(actuator_controls_status_1) : ORB_ID(actuator_controls_status_0)), // 根据是否 vtol 选择发布的 topic
	_vehicle_thrust_setpoint_pub(vtol ? ORB_ID(vehicle_thrust_setpoint_virtual_fw) : ORB_ID(vehicle_thrust_setpoint)), // 推力 setpoint 发布器
	_vehicle_torque_setpoint_pub(vtol ? ORB_ID(vehicle_torque_setpoint_virtual_fw) : ORB_ID(vehicle_torque_setpoint)), // 力矩 setpoint 发布器
	_loop_perf(perf_alloc(PC_ELAPSED, MODULE_NAME": cycle")) // 性能计时（perf），用于测量循环时间
{
	_handle_param_vt_fw_difthr_en = param_find("VT_FW_DIFTHR_EN"); // 查找差分推力参数的句柄

	/* fetch initial parameter values */
	parameters_update(); // 读取并应用初始参数值到控制器

	_rate_ctrl_status_pub.advertise(); // 广播 rate control 状态 topic，准备发布
}

// 析构函数：释放性能计时资源
FixedwingRateControl::~FixedwingRateControl()  
{
	perf_free(_loop_perf); // 释放 perf 资源
}

// 初始化函数：注册回调等
bool
FixedwingRateControl::init()
{
	if (!_vehicle_angular_velocity_sub.registerCallback()) {
		PX4_ERR("callback registration failed"); // 注册失败时输出错误日志
		return false; // 返回失败
	}

	return true; // 注册成功
}

// parameters_update: 从参数系统读取并应用 PID 和相关参数
int
FixedwingRateControl::parameters_update()
{
	// 从参数获取 P/I/D 三个轴的增益（roll, pitch, yaw），并组成 Vector3f
	const Vector3f rate_p = Vector3f(_param_fw_rr_p.get(), _param_fw_pr_p.get(), _param_fw_yr_p.get());
	const Vector3f rate_i = Vector3f(_param_fw_rr_i.get(), _param_fw_pr_i.get(), _param_fw_yr_i.get());
	const Vector3f rate_d = Vector3f(_param_fw_rr_d.get(), _param_fw_pr_d.get(), _param_fw_yr_d.get());

	_rate_control.setPidGains(rate_p, rate_i, rate_d); // 将 PID 参数设置到 _rate_control 对象中

	// 设置积分器限幅（防止积分饱和）
	_rate_control.setIntegratorLimit(
		Vector3f(_param_fw_rr_imax.get(), _param_fw_pr_imax.get(), _param_fw_yr_imax.get()));

	// 读取差分推力相关的参数句柄（如果存在）
	if (_handle_param_vt_fw_difthr_en != PARAM_INVALID) {
		param_get(_handle_param_vt_fw_difthr_en, &_param_vt_fw_difthr_en);
	}


	return PX4_OK; // 表示参数更新成功
}

// vehicle_manual_poll: 读取人工控制输入并在需要时生成速率（rate）设定或直接填充扭矩/推力 setpoint
void
FixedwingRateControl::vehicle_manual_poll()
{
	// 只有当 manual 控制开启并且处于固定翼或在非 tailsitter 的过渡模式时才处理
	if (_vcontrol_mode.flag_control_manual_enabled && _in_fw_or_transition_wo_tailsitter_transition) {

		// 无论是否有更新，都拷贝以确保 actuator 有有效值
		if (_manual_control_setpoint_sub.copy(&_manual_control_setpoint)) {

			if (_vcontrol_mode.flag_control_rates_enabled &&
			    !_vcontrol_mode.flag_control_attitude_enabled) {

				// 如果为 RATE 模式（速率控制），从摇杆生成角速率设定

				if (_vehicle_status.is_vtol_tailsitter && _vehicle_status.vehicle_type == vehicle_status_s::VEHICLE_TYPE_FIXED_WING) {
					// 对于 tailsitter 的固定翼车辆，速率设定必须以机身（hover）坐标系发布
					_rates_sp.roll = _manual_control_setpoint.yaw * radians(_param_fw_acro_z_max.get()); // 由 yaw 输入生成 roll 速率
					_rates_sp.yaw = -_manual_control_setpoint.roll * radians(_param_fw_acro_x_max.get()); // 由 roll 输入生成 yaw 速率（带符号转换）

				} else {
					// 常规 fixed-wing 映射：roll -> roll, yaw -> yaw
					_rates_sp.roll = _manual_control_setpoint.roll * radians(_param_fw_acro_x_max.get());
					_rates_sp.yaw = _manual_control_setpoint.yaw * radians(_param_fw_acro_z_max.get());
				}

				_rates_sp.timestamp = hrt_absolute_time(); // 填充时间戳
				_rates_sp.pitch = -_manual_control_setpoint.pitch * radians(_param_fw_acro_y_max.get()); // pitch 映射（带符号）
				_rates_sp.thrust_body[0] = (_manual_control_setpoint.throttle + 1.f) * .5f; // 将 throttle [-1,1] 映射到 [0,1]

				_rate_sp_pub.publish(_rates_sp); // 发布速率 setpoint

			} else {
				// 手动/直接控制，填充 FW-frame 下的扭矩（注意接口会把它转换为机身 frame）
				const float airspeed_scaling_sq = _airspeed_scaling * _airspeed_scaling; // 空速缩放的平方

				// roll 控制输入 -> 扭矩指令（受 trim 和空速缩放影响，且约束在 [-1,1]）
				_vehicle_torque_setpoint.xyz[0] = math::constrain(_manual_control_setpoint.roll * _param_fw_man_r_sc.get() +
										  _param_trim_roll.get() * airspeed_scaling_sq, -1.f, 1.f);
				_vehicle_torque_setpoint.xyz[1] = math::constrain(-_manual_control_setpoint.pitch * _param_fw_man_p_sc.get() +
										  _param_trim_pitch.get() * airspeed_scaling_sq, -1.f, 1.f);
				_vehicle_torque_setpoint.xyz[2] = math::constrain(_manual_control_setpoint.yaw * _param_fw_man_y_sc.get() +
										  _param_trim_yaw.get() * airspeed_scaling_sq, -1.f, 1.f);

				// 推力 setpoint 同样映射并约束到 [0,1]
				_vehicle_thrust_setpoint.xyz[0] = math::constrain((_manual_control_setpoint.throttle + 1.f) * .5f, 0.f, 1.f);
			}
		}
	}
}

// vehicle_land_detected_poll: 检查着陆检测订阅并更新 _landed 标志
void
FixedwingRateControl::vehicle_land_detected_poll()
{
	if (_vehicle_land_detected_sub.updated()) {
		vehicle_land_detected_s vehicle_land_detected {};

		if (_vehicle_land_detected_sub.copy(&vehicle_land_detected)) {
			_landed = vehicle_land_detected.landed; // 将消息中的 landed 字段保存到成员变量
		}
	}
}

// get_airspeed_and_update_scaling: 获取空速并更新 _airspeed_scaling（用于缩放控制量）
float FixedwingRateControl::get_airspeed_and_update_scaling()
{
	_airspeed_validated_sub.update(); // 更新订阅缓存
	const bool airspeed_valid = PX4_ISFINITE(_airspeed_validated_sub.get().calibrated_airspeed_m_s)
					    && (hrt_elapsed_time(&_airspeed_validated_sub.get().timestamp) < 1_s); // 空速数据是否可用且最近

	// 如果没有可用空速量测，默认使用修整空速（trim）作为估计
	float airspeed = _param_fw_airspd_trim.get();

	if (_param_fw_use_airspd.get() && airspeed_valid) {
		/* prevent numerical drama by requiring 0.5 m/s minimal speed */
		airspeed = math::max(0.5f, _airspeed_validated_sub.get().calibrated_airspeed_m_s); // 防止数值问题，最小 0.5 m/s

	} else {
		// 对于 VTOL 且处于悬停（旋翼）模式，若无空速则假设最低空速为失速速度（更保守）
		if (_vehicle_status.is_vtol && _vehicle_status.vehicle_type == vehicle_status_s::VEHICLE_TYPE_ROTARY_WING
		    && !_vehicle_status.in_transition_mode) {
			airspeed = _param_fw_airspd_stall.get();
		}
	}

	/*
	 * For scaling our actuators using anything less than the stall
	 * speed doesn't make any sense - its the strongest reasonable deflection we
	 * want to do in flight and it's the baseline a human pilot would choose.
	 *
	 * Forcing the scaling to this value allows reasonable handheld tests.
	 */

	// 判断是否启用空速缩放
	if (_param_fw_arsp_scale_en.get()) {
		const float min_airspeed = math::max(_param_fw_airspd_stall.get(), 0.1f); // 最小空速，至少 0.1 m/s
		const float airspeed_constrained = math::max(airspeed, min_airspeed); // 约束空速
		_airspeed_scaling = _param_fw_airspd_trim.get() / airspeed_constrained; // 根据修整空速计算缩放因子

	} else {
		_airspeed_scaling = 1.0f; // 不缩放
	}

	return airspeed; // 返回用于其它计算的空速
}

// Run: 主循环函数（由调度器周期性调用）
void FixedwingRateControl::Run()
{
	if (should_exit()) {
		_vehicle_angular_velocity_sub.unregisterCallback(); // 注销回调
		exit_and_cleanup(); // 清理并退出
		return;
	}

	perf_begin(_loop_perf); // 开始计时性能监测

	// 只有当角速度更新或超过超时才运行控制器（避免空跑）
	if (_vehicle_angular_velocity_sub.updated() || (hrt_elapsed_time(&_last_run) > 20_ms)) { // TODO: 考虑更严格的速率控制

		// 只在参数有更新时做更新
		bool params_updated = _parameter_update_sub.updated();

		// 检查是否有参数更新
		if (params_updated) {
			// 清除 update 标志并读取
			parameter_update_s pupdate;
			_parameter_update_sub.copy(&pupdate);

			// 从存储更新模块参数
			updateParams();
			parameters_update(); // 将参数应用于控制器
		}

		float dt = 0.f; // 时间步长初始化

		static constexpr float DT_MIN = 0.002f; // 最小 dt（2 ms）
		static constexpr float DT_MAX = 0.04f; // 最大 dt（40 ms）

		vehicle_angular_velocity_s vehicle_angular_velocity{}; // 临时变量，保存角速度消息

		if (_vehicle_angular_velocity_sub.copy(&vehicle_angular_velocity)) {
			dt = math::constrain((vehicle_angular_velocity.timestamp_sample - _last_run) * 1e-6f, DT_MIN, DT_MAX); // 计算 dt 并约束
			_last_run = vehicle_angular_velocity.timestamp_sample; // 更新上次运行时间戳
		}

		if (dt < DT_MIN || dt > DT_MAX) {
			const hrt_abstime time_now_us = hrt_absolute_time(); // 获取当前时间
			dt = math::constrain((time_now_us - _last_run) * 1e-6f, DT_MIN, DT_MAX); // 备用 dt 计算
			_last_run = time_now_us;
		}

		vehicle_angular_velocity_s angular_velocity{};
		_vehicle_angular_velocity_sub.copy(&angular_velocity); // 拷贝角速度消息

		Vector3f rates(angular_velocity.xyz); // 当前角速度向量
		Vector3f angular_accel{angular_velocity.xyz_derivative}; // 角加速度（导数）

		// Tailsitter: 对于 tailsitter，需要把测得的角速率转换到固定翼控制器使用的坐标系
		if (_vehicle_status.is_vtol_tailsitter) {
			rates = Vector3f(-angular_velocity.xyz[2], angular_velocity.xyz[1], angular_velocity.xyz[0]); // 轴变换
			angular_accel = Vector3f(-angular_velocity.xyz_derivative[2], angular_velocity.xyz_derivative[1],
							 angular_velocity.xyz_derivative[0]);
		}

		// 更新 vehicle status（必须在 vehicle_control_mode poll 之前），以保证过渡期间速率设定被发布
		_vehicle_status_sub.update(&_vehicle_status);
		const bool is_in_transition_except_tailsitter = _vehicle_status.in_transition_mode
							&& !_vehicle_status.is_vtol_tailsitter; // 是否处于非 tailsitter 的过渡模式
		const bool is_fixed_wing = _vehicle_status.vehicle_type == vehicle_status_s::VEHICLE_TYPE_FIXED_WING; // 是否为固定翼
		_in_fw_or_transition_wo_tailsitter_transition =  is_fixed_wing || is_in_transition_except_tailsitter; // 内部标志

		_vehicle_control_mode_sub.update(&_vcontrol_mode); // 更新控制模式

		vehicle_land_detected_poll(); // 更新着陆检测标志

		vehicle_manual_poll(); // 处理人工输入
		vehicle_land_detected_poll(); // 再次检查（因为 manual_poll 可能改变状态）

		/* if we are in rotary wing mode, do nothing */
		if (_vehicle_status.vehicle_type == vehicle_status_s::VEHICLE_TYPE_ROTARY_WING && !_vehicle_status.is_vtol) {
			perf_end(_loop_perf); // 结束性能计时
			return; // 旋翼模式下不执行固定翼速率控制
		}

		if (_vcontrol_mode.flag_control_rates_enabled) {

			const float airspeed = get_airspeed_and_update_scaling(); // 获取空速并更新缩放因子

			/* reset integrals where needed */
			if (_rates_sp.reset_integral) {
				_rate_control.resetIntegral(); // 如果速率设定请求复位积分，则清除积分
			}

			// 如果着陆或不在可以运行固定翼姿态控制的状态，也复位积分
			if (_landed || !_in_fw_or_transition_wo_tailsitter_transition) {

				_rate_control.resetIntegral();
			}

			// Update saturation status from control allocation feedback
			// TODO: send the unallocated value directly for better anti-windup
			Vector3<bool> diffthr_enabled(
				_param_vt_fw_difthr_en & static_cast<int32_t>(VTOLFixedWingDifferentialThrustEnabledBit::ROLL_BIT),
				_param_vt_fw_difthr_en & static_cast<int32_t>(VTOLFixedWingDifferentialThrustEnabledBit::PITCH_BIT),
				_param_vt_fw_difthr_en & static_cast<int32_t>(VTOLFixedWingDifferentialThrustEnabledBit::YAW_BIT)
			);

			if (_vehicle_status.is_vtol_tailsitter) {
				// 对于 tailsitter，需要交换 roll 和 yaw 的索引
				diffthr_enabled.swapRows(0, 2);
			}

			// 对由差分推力控制的轴（通常在 VTOL）进行饱和处理
			control_allocator_status_s control_allocator_status;

			// 如果差分推力被启用，假设该轴只有推力提供力矩，所以使用第 0 个 control allocator 的 unallocated_torque
			if (_control_allocator_status_subs[0].update(&control_allocator_status)) {
				for (size_t i = 0; i < 3; i++) {
					if (diffthr_enabled(i)) {
						_rate_control.setPositiveSaturationFlag(i, control_allocator_status.unallocated_torque[i] > FLT_EPSILON);
						_rate_control.setNegativeSaturationFlag(i, control_allocator_status.unallocated_torque[i] < -FLT_EPSILON);
					}
				}
			}

			// 对由控制面（control surfaces）控制的轴设置饱和标志（根据当前 vehicle 是否 vtol 选择索引）
			if (_control_allocator_status_subs[_vehicle_status.is_vtol ? 1 : 0].update(&control_allocator_status)) {
				for (size_t i = 0; i < 3; i++) {
					if (!diffthr_enabled(i)) {
						_rate_control.setPositiveSaturationFlag(i, control_allocator_status.unallocated_torque[i] > FLT_EPSILON);
						_rate_control.setNegativeSaturationFlag(i, control_allocator_status.unallocated_torque[i] < -FLT_EPSILON);
					}
				}
			}

			/* bi-linear interpolation over airspeed for actuator trim scheduling */
			Vector3f trim(_param_trim_roll.get(), _param_trim_pitch.get(), _param_trim_yaw.get()); // 初始 trim 值
			trim *= _airspeed_scaling * _airspeed_scaling; // 按空速缩放平方调整 trim

			if (airspeed < _param_fw_airspd_trim.get()) {
				// 当空速小于修整空速时，使用从低速到 trim 速度的插值补偿
				trim(0) += interpolate(airspeed, _param_fw_airspd_min.get(), _param_fw_airspd_trim.get(),
						       _param_fw_dtrim_r_vmin.get(),
						       0.0f);
				trim(1) += interpolate(airspeed, _param_fw_airspd_min.get(), _param_fw_airspd_trim.get(),
						       _param_fw_dtrim_p_vmin.get(),
						       0.0f);
				trim(2) += interpolate(airspeed, _param_fw_airspd_min.get(), _param_fw_airspd_trim.get(),
						       _param_fw_dtrim_y_vmin.get(),
						       0.0f);

			} else {
				// 当空速大于等于修整空速时，使用从 trim 到最大空速的插值补偿
				trim(0) += interpolate(airspeed, _param_fw_airspd_trim.get(), _param_fw_airspd_max.get(), 0.0f,
					       _param_fw_dtrim_r_vmax.get());
				trim(1) += interpolate(airspeed, _param_fw_airspd_trim.get(), _param_fw_airspd_max.get(), 0.0f,
					       _param_fw_dtrim_p_vmax.get());
				trim(2) += interpolate(airspeed, _param_fw_airspd_trim.get(), _param_fw_airspd_max.get(), 0.0f,
					       _param_fw_dtrim_y_vmax.get());
			}

			if (_vcontrol_mode.flag_control_rates_enabled) {
				_rates_sp_sub.update(&_rates_sp); // 更新速率设定订阅

				Vector3f body_rates_setpoint = Vector3f(_rates_sp.roll, _rates_sp.pitch, _rates_sp.yaw); // 将消息转换为 Vector3f

				// Tailsitter: 对 tailsitter 做对应的坐标系变换（把 hover frame 的 setpoint 旋转到 fixed-wing frame）
				if (_vehicle_status.is_vtol_tailsitter) {
					body_rates_setpoint = Vector3f(-_rates_sp.yaw, _rates_sp.pitch, _rates_sp.roll);
				}

				const Vector3f gain_ff(_param_fw_rr_ff.get(), _param_fw_pr_ff.get(), _param_fw_yr_ff.get()); // 前馈增益
				const Vector3f scaled_gain_ff = gain_ff / _airspeed_scaling; // 根据空速缩放前馈
				_rate_control.setFeedForwardGain(scaled_gain_ff); // 设置前馈增益

				// 运行速率控制器：得到角加速度的设定量
				const Vector3f angular_acceleration_setpoint = _rate_control.update(rates, body_rates_setpoint, angular_accel, dt,
												_landed);

				Vector3f control_u = angular_acceleration_setpoint * _airspeed_scaling * _airspeed_scaling; // 将角加速度映射回控制量并按空速平方缩放

				// 若处于 Acro 模式且禁用了 yaw 的速率控制，则使用手动输入替代 yaw 控制
				if (!_vcontrol_mode.flag_control_attitude_enabled && _vcontrol_mode.flag_control_manual_enabled
				    && !_param_fw_acro_yaw_en.get()) {
					control_u(2) = _manual_control_setpoint.yaw * _param_fw_man_y_sc.get(); // 使用手动 yaw 输入
					_rate_control.resetIntegral(2); // 重置 yaw 轴的积分量
				}

				if (control_u.isAllFinite()) {
					matrix::constrain(control_u + trim, -1.f, 1.f).copyTo(_vehicle_torque_setpoint.xyz); // 约束并写入扭矩 setpoint

				} else {
					_rate_control.resetIntegral(); // 若数学异常，则复位积分并仅发布 trim
					trim.copyTo(_vehicle_torque_setpoint.xyz);
				}

				/* throttle passed through if it is finite */
				_vehicle_thrust_setpoint.xyz[0] = PX4_ISFINITE(_rates_sp.thrust_body[0]) ? _rates_sp.thrust_body[0] : 0.0f; // 推力透传

				/* scale effort by battery status */
				if (_param_fw_bat_scale_en.get() && _vehicle_thrust_setpoint.xyz[0] > 0.1f) {

					if (_battery_status_sub.updated()) {
						battery_status_s battery_status{};

						if (_battery_status_sub.copy(&battery_status) && battery_status.connected && battery_status.scale > 0.f) {
							_battery_scale = battery_status.scale; // 从电池状态消息更新缩放系数
						}
					}

					_vehicle_thrust_setpoint.xyz[0] *= _battery_scale; // 将推力按电池缩放
				}
			}

			// publish rate controller status
			rate_ctrl_status_s rate_ctrl_status{};
			_rate_control.getRateControlStatus(rate_ctrl_status); // 从 rate 控制器获取状态数据
			rate_ctrl_status.timestamp = hrt_absolute_time(); // 填充时间戳

			_rate_ctrl_status_pub.publish(rate_ctrl_status); // 发布状态

		} else {
			// 如果速率控制没开（full manual），复位积分
			_rate_control.resetIntegral();
		}

		// Add feed-forward from roll control output to yaw control output
		// This can be used to counteract the adverse yaw effect when rolling the plane
		_vehicle_torque_setpoint.xyz[2] = math::constrain(_vehicle_torque_setpoint.xyz[2] + _param_fw_rll_to_yaw_ff.get() *
								  _vehicle_torque_setpoint.xyz[0], -1.f, 1.f); // 将 roll 的输出按系数影响到 yaw，处理副偏航

		// Tailsitter: rotate back to body frame from airspeed frame
		if (_vehicle_status.is_vtol_tailsitter) {
			const float helper = _vehicle_torque_setpoint.xyz[0];
			_vehicle_torque_setpoint.xyz[0] = _vehicle_torque_setpoint.xyz[2];
			_vehicle_torque_setpoint.xyz[2] = -helper; // 做回变换以匹配机身坐标
		}

		/* Only publish if any of the proper modes are enabled */
		if (_vcontrol_mode.flag_control_rates_enabled ||
		    _vcontrol_mode.flag_control_attitude_enabled ||
		    _vcontrol_mode.flag_control_manual_enabled) {
			{
				_vehicle_thrust_setpoint.timestamp = hrt_absolute_time(); // 填充时间戳
				_vehicle_thrust_setpoint.timestamp_sample = angular_velocity.timestamp_sample; // 填充采样时间
				_vehicle_thrust_setpoint_pub.publish(_vehicle_thrust_setpoint); // 发布推力 setpoint

				_vehicle_torque_setpoint.timestamp = hrt_absolute_time();
				_vehicle_torque_setpoint.timestamp_sample = angular_velocity.timestamp_sample;
				_vehicle_torque_setpoint_pub.publish(_vehicle_torque_setpoint); // 发布扭矩 setpoint
			}
		}

		updateActuatorControlsStatus(dt); // 更新执行器功率/能量统计

		// Manual flaps/spoilers control, also active in VTOL Hover. Is handled and published in FW Position controller/VTOL module if Auto.
		if (_vcontrol_mode.flag_control_manual_enabled) {

			// Flaps control
			float flaps_control = 0.f; // 默认无襟副翼控制

			/* map flaps by default to manual if valid */
			if (PX4_ISFINITE(_manual_control_setpoint.flaps)) {
				flaps_control = math::max(_manual_control_setpoint.flaps, 0.f); // 不接受负的开关值
			}

			normalized_unsigned_setpoint_s flaps_setpoint;
			flaps_setpoint.timestamp = hrt_absolute_time();
			flaps_setpoint.normalized_setpoint = flaps_control; // 填充结构体并发布
			_flaps_setpoint_pub.publish(flaps_setpoint);

			// Spoilers control（扰流板）
			float spoilers_control = 0.f; // 默认无扰流板

			switch (_param_fw_spoilers_man.get()) {
			case 0:
				break; // 不手动控制

			case 1:
				// 将 flaps 输入映射为 spoilers（不接受负值）
				spoilers_control = PX4_ISFINITE(_manual_control_setpoint.flaps) ? math::max(_manual_control_setpoint.flaps, 0.f) : 0.f;
				break;

			case 2:
				// 将 aux1 输入映射为 spoilers（不接受负值）
				spoilers_control = PX4_ISFINITE(_manual_control_setpoint.aux1) ? math::max(_manual_control_setpoint.aux1, 0.f) : 0.f;
				break;
			}

			normalized_unsigned_setpoint_s spoilers_setpoint;
			spoilers_setpoint.timestamp = hrt_absolute_time();
			spoilers_setpoint.normalized_setpoint = spoilers_control;
			_spoilers_setpoint_pub.publish(spoilers_setpoint); // 发布扰流板设定
		}
	}

	// backup schedule: 延迟再次被调度运行，确保周期性执行（20 ms）
	ScheduleDelayed(20_ms);

	perf_end(_loop_perf); // 结束性能计时
}

// updateActuatorControlsStatus: 计算控制面消耗的 "能量" 指标并周期性发布
void FixedwingRateControl::updateActuatorControlsStatus(float dt)
{
	for (int i = 0; i < 3; i++) {

		// 我们假设舵面仅在移动时消耗功率，通过与上一次控制差值的平方积分来估计
		const float control_signal = _vehicle_torque_setpoint.xyz[i] - _control_prev[i]; // 本次控制与上次之差
		_control_prev[i] = _vehicle_torque_setpoint.xyz[i]; // 保存本次值用于下一次比较

		_control_energy[i] += control_signal * control_signal * dt; // 累积（差值平方 * 时间）作为能量指标
	}

	_energy_integration_time += dt; // 累积积分时间

	if (_energy_integration_time > 500e-3f) { // 超过 0.5s 时发布一次

		actuator_controls_status_s status;
		status.timestamp = _vehicle_torque_setpoint.timestamp; // 使用扭矩 setpoint 的时间戳

		for (int i = 0; i < 3; i++) {
			status.control_power[i] = _control_energy[i] / _energy_integration_time; // 平均功率
			_control_energy[i] = 0.f; // 清零能量累积
		}

		_actuator_controls_status_pub.publish(status); // 发布状态
		_energy_integration_time = 0.f; // 重置积分时间
	}
}

// task_spawn: 模块入口，用于创建实例并注册到工作队列
int FixedwingRateControl::task_spawn(int argc, char *argv[])
{
	bool vtol = false; // 默认非 VTOL

	if (argc > 1) {
		if (strcmp(argv[1], "vtol") == 0) {
			vtol = true; // 如果传入参数为 "vtol" 则以 VTOL 模式启动
		}
	}

	FixedwingRateControl *instance = new FixedwingRateControl(vtol); // 创建实例

	if (instance) {
		_object.store(instance); // 存储到静态对象指针，便于后续访问
		_task_id = task_id_is_work_queue; // 标记任务类型为工作队列

		if (instance->init()) {
			return PX4_OK; // 初始化成功返回 OK
		}

	} else {
		PX4_ERR("alloc failed"); // 内存分配失败
	}

	delete instance; // 清理
	_object.store(nullptr);
	_task_id = -1;

	return PX4_ERROR; // 如果执行到这里说明启动失败
}

// custom_command: 自定义命令处理（这里未实现，默认打印用法）
int FixedwingRateControl::custom_command(int argc, char *argv[])
{
	return print_usage("unknown command");
}

// print_usage: 打印模块使用说明
int FixedwingRateControl::print_usage(const char *reason)
{
	if (reason) {
		PX4_WARN("%s\n", reason); // 打印警告原因
	}

	PRINT_MODULE_DESCRIPTION(
		R"DESCR_STR(
	### Description
	fw_rate_control is the fixed-wing rate controller.

	)DESCR_STR");

	PRINT_MODULE_USAGE_NAME("fw_rate_control", "controller");
	PRINT_MODULE_USAGE_COMMAND("start");
	PRINT_MODULE_USAGE_ARG("vtol", "VTOL mode", true);
	PRINT_MODULE_USAGE_DEFAULT_COMMANDS();

	return 0; // 返回成功
}

// C 风格导出主入口，供模块加载器调用
extern "C" __EXPORT int fw_rate_control_main(int argc, char *argv[])
{
	return FixedwingRateControl::main(argc, argv); // 调用类的 main 实现（由 ModuleBase 提供）
}
