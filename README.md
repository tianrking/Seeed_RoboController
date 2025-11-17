# FTServo 工厂校准工具 (FTServo Factory Calibration Tool)

这是一个完整的FTServo舵机工厂校准工具包，包含双串口校准GUI界面和所有必要的脚本。

## 文件说明 (File Description)

- `factory_calibration_tool.py` - 主GUI应用程序，支持双串口舵机校准
- `servo_middle_calibration.py` - 舵机中位值校准脚本
- `servo_quick_calibration.py` - 快速校准脚本
- `servo_center_test.py` - 舵机中心测试脚本
- `servo_disable.py` - 舵机失能脚本
- `servo_remote_control.py` - 遥控操作脚本
- `scservo_sdk/` - SCServo SDK文件夹，包含舵机通信库
- `setup.py` - 自动化安装和检查脚本

## 使用方法 (Usage)

1. 安装依赖：
   ```bash
   pip install PySide6 pyserial
   ```

2. 运行安装检查（推荐）：
   ```bash
   python setup.py
   ```

3. 运行主程序：
   ```bash
   python factory_calibration_tool.py
   ```

4. 或指定串口运行：
   ```bash
   python factory_calibration_tool.py --port1 COM1 --port2 COM2
   ```

## 功能特性 (Features)

- 双串口同时校准支持
- 动态串口选择
- 中位校准、中位测试、失能电机功能
- 水平布局UI，美观节省空间
- 连接稳定性和智能重试机制

## 默认串口 (Default Ports)

- Windows: COM1, COM2
- Linux: /dev/ttyUSB0, /dev/ttyUSB1 或 /dev/ttyACM0, /dev/ttyACM1

## 注意事项 (Notes)

- 确保舵机正确连接到指定串口
- 校准过程中请勿移动舵机
- 建议在校准前先进行中位测试