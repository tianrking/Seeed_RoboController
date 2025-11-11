# FTServo Advanced Control System - API Reference

## 概述

本文档描述了FTServo高级控制系统的完整API接口，包括基于逆向工程分析发现的所有硬件功能。

## 核心类

### FTServoController

主控制器类，提供完整的舵机控制功能。

#### 初始化

```python
controller = FTServoController(port_name='COM8', baud_rate=1000000, protocol='hls')
```

#### 主要方法

##### 连接管理
- `initialize(protocol='hls') -> bool` - 初始化控制器
- `scan_servos(start_id=1, end_id=20) -> List[Dict]` - 扫描舵机
- `disconnect()` - 断开连接

##### 基础控制
- `move_servo(servo_id, position, speed=100, acceleration=50) -> bool` - 移动舵机
- `stop_servo(servo_id) -> bool` - 停止舵机
- `get_servo_status(servo_id) -> Dict` - 获取舵机状态

##### 高级功能
- `monitor_temperature(duration=60, interval=1.0) -> Dict` - 温度监控
- `set_pid_params(servo_id, position_pid=None, speed_pid=None, startup_torque=None) -> bool` - PID参数设置
- `configure_safety(servo_id, temp_limit=None, voltage_range=None, overload_settings=None) -> bool` - 安全配置
- `get_diagnostics(servo_id) -> Dict` - 获取诊断信息

### ConnectionManager

连接管理器，负责串口通信和基础协议处理。

#### 方法
- `connect(protocol='hls') -> bool` - 连接到舵机
- `disconnect()` - 断开连接
- `ping(servo_id) -> Tuple[model_number, result, error]` - ping舵机
- `read_memory(servo_id, address, length) -> Tuple[data, result, error]` - 读取内存
- `write_memory(servo_id, address, length, data) -> Tuple[result, error]` - 写入内存

### BasicControl

基础控制模块，提供位置、速度、扭矩控制。

#### 方法
- `write_position(servo_id, position, speed, acceleration) -> Tuple[result, error]` - 写入位置
- `read_position(servo_id) -> Tuple[position, result, error]` - 读取位置
- `write_speed(servo_id, speed) -> Tuple[result, error]` - 写入速度
- `read_speed(servo_id) -> Tuple[speed, result, error]` - 读取速度
- `enable_torque(servo_id, enable=True) -> Tuple[result, error]` - 扭矩使能

### StatusMonitor

状态监控模块，基于逆向工程发现的高级监控功能。

#### 方法
- `read_temperature(servo_id) -> Tuple[temperature, result, error]` - 读取温度 (地址63)
- `read_temperature_limit(servo_id) -> Tuple[limit, result, error]` - 读取温度上限 (地址13)
- `read_voltage(servo_id) -> Tuple[voltage, result, error]` - 读取电压
- `read_current(servo_id) -> Tuple[current, result, error]` - 读取电流 (地址68-69)
- `read_hardware_error_status(servo_id) -> Tuple[error_status, result, error]` - 读取硬件错误状态 (地址66)
- `get_complete_status(servo_id) -> Dict` - 获取完整状态
- `monitor_temperature(duration, interval=1.0) -> Dict` - 连续温度监控

### PIDController

PID控制模块，基于逆向工程发现的PID参数调节功能。

#### 方法
- `read_position_pid(servo_id) -> Tuple[pid_params, result, error]` - 读取位置PID (地址21-23)
- `write_position_pid(servo_id, p_gain, i_gain, d_gain) -> Tuple[result, error]` - 写入位置PID
- `read_speed_pid(servo_id) -> Tuple[pid_params, result, error]` - 读取速度PID (地址37,39)
- `write_speed_pid(servo_id, p_gain, i_gain) -> Tuple[result, error]` - 写入速度PID
- `read_startup_torque(servo_id) -> Tuple[torque, result, error]` - 读取启动扭矩 (地址24)
- `write_startup_torque(servo_id, startup_torque) -> Tuple[result, error]` - 写入启动扭矩
- `set_pid_params(servo_id, position_pid=None, speed_pid=None, startup_torque=None) -> bool` - 综合设置PID参数
- `reset_pid_to_default(servo_id) -> bool` - 重置PID为默认值

### SafetyManager

安全保护模块，基于逆向工程发现的安全配置功能。

#### 方法
- `configure_temperature_limit(servo_id, temperature_limit) -> Tuple[result, error]` - 配置温度限制 (地址13)
- `configure_voltage_limits(servo_id, min_voltage, max_voltage) -> Tuple[result, error]` - 配置电压限制 (地址14-15)
- `configure_safety(servo_id, temp_limit=None, voltage_range=None, overload_settings=None) -> bool` - 综合安全配置

### HardwareConfig

硬件配置模块，基于逆向工程发现的硬件配置功能。

#### 方法
- `set_servo_id(current_id, new_id) -> Tuple[result, error]` - 设置舵机ID (地址5)
- `read_servo_id(servo_id) -> Tuple[id, result, error]` - 读取舵机ID

### DiagnosticTools

诊断工具模块，基于逆向工程发现的诊断功能。

#### 方法
- `get_firmware_version(servo_id) -> Dict` - 获取固件版本 (地址0-1,3-4)
- `get_full_diagnostics(servo_id) -> Dict` - 获取完整诊断信息

## 逆向工程发现的内存地址

### 基础监控地址
- **地址63**: 当前温度寄存器
- **地址13**: 温度上限设置
- **地址68-69**: 当前电流
- **地址66**: 硬件错误状态
- **地址64**: 硬件错误状态 (备选)

### PID控制地址
- **地址21**: 位置P增益
- **地址22**: 位置D增益
- **地址23**: 位置I增益
- **地址37**: 速度P增益
- **地址39**: 速度I增益
- **地址24**: 启动扭矩

### 安全保护地址
- **地址13**: 温度限制
- **地址14**: 最大输入电压
- **地址15**: 最小输入电压

### 硬件信息地址
- **地址0**: 固件主版本
- **地址1**: 固件副版本
- **地址3**: 舵机主版本
- **地址4**: 舵机副版本

## 使用示例

### 基础使用
```python
# 创建控制器
controller = FTServoController('COM8')

# 初始化
controller.initialize('hls')

# 扫描舵机
servos = controller.scan_servos()

# 移动舵机
controller.move_servo(1, 2048, 100, 50)

# 读取状态
status = controller.get_servo_status(1)

# 断开连接
controller.disconnect()
```

### 高级功能使用
```python
# 温度监控
temp_data = controller.monitor_temperature(duration=60)

# PID参数设置
controller.set_pid_params(1, position_pid=[32, 0, 32], speed_pid=[10, 200])

# 安全配置
controller.configure_safety(1, temp_limit=75, voltage_range=(6.0, 14.0))

# 获取诊断信息
diagnostics = controller.get_diagnostics(1)
```

### 逆向工程功能使用
```python
# 直接使用状态监控模块
monitor = StatusMonitor(connection)

# 读取温度 (逆向发现)
temperature, result, error = monitor.read_temperature(1)

# 读取温度限制 (逆向发现)
temp_limit, result, error = monitor.read_temperature_limit(1)

# 使用PID控制器
pid_ctrl = PIDController(connection)

# 设置位置PID (逆向发现)
result, error = pid_ctrl.write_position_pid(1, 40, 5, 30)

# 读取速度PID (逆向发现)
speed_pid, result, error = pid_ctrl.read_speed_pid(1)
```

## 错误代码

- `COMM_SUCCESS = 0`: 通信成功
- `COMM_PORT_BUSY = -1`: 端口忙
- `COMM_TX_FAIL = -2`: 发送失败
- `COMM_RX_FAIL = -3`: 接收失败
- `COMM_RX_TIMEOUT = -4`: 接收超时
- `COMM_RX_CORRUPT = -5`: 数据损坏
- `ERROR_SERVO_NOT_FOUND = -100`: 舵机未找到
- `ERROR_INVALID_PARAMETER = -101`: 无效参数
- `ERROR_OPERATION_FAILED = -102`: 操作失败
- `ERROR_PERMISSION_DENIED = -103`: 权限被拒绝

## 注意事项

1. **EEPROM操作**: 涉及地址13, 21-23, 37-39, 24等需要先调用`unLockEprom()`解锁，操作完成后调用`LockEprom()`锁定。

2. **数据格式**:
   - 温度、电压、增益等为单字节无符号数
   - 位置、速度、电流等为双字节有符号数

3. **安全考虑**: 直接访问逆向发现的地址可能影响舵机稳定性，建议在非关键应用中测试。

4. **兼容性**: 不同型号的FTServo舵机可能对某些逆向地址的支持有所不同。

---

*基于FTServo硬件逆向工程分析的高级控制系统API文档*