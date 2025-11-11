# FTServo Advanced Control System

## 📋 项目概述

基于逆向工程分析的FTServo舵机高级控制系统，提供了完整的跨平台Python上位机解决方案，实现了官方SDK未公开的全部硬件功能。

## 🏗️ 项目结构

```
diy_tool/
├── README.md                    # 项目说明文档
├── main.py                      # 主程序入口
├── config/                      # 配置文件
│   ├── __init__.py
│   ├── settings.py              # 全局配置
│   └── memory_map.py            # 内存映射定义
├── core/                        # 核心模块
│   ├── __init__.py
│   ├── servo_manager.py         # 舵机管理器
│   ├── protocol_handler.py      # 协议处理器
│   └── connection_manager.py    # 连接管理器
├── modules/                     # 功能模块
│   ├── __init__.py
│   ├── basic_control.py         # 基础控制模块
│   ├── status_monitor.py        # 状态监控模块
│   ├── pid_controller.py        # PID控制模块
│   ├── safety_manager.py        # 安全保护模块
│   ├── hardware_config.py       # 硬件配置模块
│   └── diagnostic_tools.py      # 诊断工具模块
├── utils/                       # 工具类
│   ├── __init__.py
│   ├── logger.py                # 日志工具
│   ├── data_parser.py           # 数据解析工具
│   └── ui_helpers.py            # UI辅助工具
├── tests/                       # 测试文件
│   ├── __init__.py
│   ├── test_basic_control.py
│   ├── test_pid_control.py
│   └── test_safety.py
└── docs/                        # 详细文档
    ├── api_reference.md         # API参考文档
    ├── user_guide.md            # 用户使用指南
    └── reverse_engineering.md   # 逆向工程分析报告
```

## 🔧 功能模块

### 1. 基础控制模块 (Basic Control)
- ✅ 位置控制
- ✅ 速度控制
- ✅ 扭矩控制
- ✅ 多舵机同步控制

### 2. 状态监控模块 (Status Monitor)
- ✅ 实时温度监控
- ✅ 电压电流监控
- ✅ 位置速度反馈
- ✅ 错误状态诊断

### 3. PID控制模块 (PID Controller)
- 🆕 位置PID参数调节
- 🆕 速度PID参数调节
- 🆕 启动扭矩配置
- 🆕 控制性能优化

### 4. 安全保护模块 (Safety Manager)
- 🆕 温度保护设置
- 🆕 电压保护范围
- 🆕 过载保护配置
- 🆕 过流保护设置

### 5. 硬件配置模块 (Hardware Config)
- 🆕 舵机ID管理
- 🆕 通信参数配置
- 🆕 运动限制设置
- 🆕 校准功能

### 6. 诊断工具模块 (Diagnostic Tools)
- 🆕 固件版本查询
- 🆕 硬件错误分析
- 🆕 性能监控
- 🆕 系统健康检查

## 🚀 快速开始

### 环境要求
- Python 3.7+
- FTServo舵机及通信设备
- 支持Windows/Linux/macOS

### 安装依赖
```bash
pip install pyserial tkinter
```

### 基本使用
```python
from diy_tool.main import FTServoController

# 创建控制器实例
controller = FTServoController(port_name='COM8')

# 连接舵机
controller.connect()

# 扫描舵机
servos = controller.scan_servos()

# 温度监控
controller.monitor_temperature()

# PID调节
controller.set_pid_params(servo_id=1, position_pid=[32, 0, 32])

# 关闭连接
controller.disconnect()
```

## 📚 详细文档

- [API参考文档](docs/api_reference.md)
- [用户使用指南](docs/user_guide.md)
- [逆向工程分析](docs/reverse_engineering.md)

## 🎯 核心特性

### 🔬 基于逆向工程
- 利用逆向分析获取的64个内存地址
- 实现官方SDK未公开的61%功能
- 完整的硬件能力访问

### 🛡️ 安全可靠
- 完善的错误处理机制
- 安全的EEPROM操作
- 多重保护机制

### 🌐 跨平台支持
- Windows/Linux/macOS兼容
- 统一的API接口
- 灵活的配置系统

### 📊 智能监控
- 实时状态监控
- 智能警告系统
- 详细的诊断报告

## 🤝 贡献指南

欢迎提交问题报告和功能请求，详细指南请参考[贡献文档](docs/contributing.md)。

## 📄 许可证

本项目基于MIT许可证开源，详见[LICENSE](LICENSE)文件。

---

*基于FTServo硬件逆向工程分析的高级控制系统*