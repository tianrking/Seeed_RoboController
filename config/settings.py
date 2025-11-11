#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Global Settings
全局配置和常量定义
"""

import os
import sys

# 添加SDK路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from scservo_sdk import *


class CommunicationConfig:
    """通信配置"""

    # 默认串口配置
    DEFAULT_PORT = 'COM8' if os.name == 'nt' else '/dev/ttyUSB0'
    DEFAULT_BAUDRATE = 1000000

    # 支持的波特率
    BAUDRATES = {
        0: 1000000,
        1: 500000,
        2: 250000,
        3: 128000,
        4: 115200,
        5: 76800,
        6: 57600,
        7: 38400
    }

    # 协议类型
    PROTOCOLS = {
        'hls': hls,
        'scscl': scscl,
        'sms_sts': sms_sts
    }

    # 默认协议
    DEFAULT_PROTOCOL = 'hls'


class ServoConfig:
    """舵机配置"""

    # 位置范围
    MIN_POSITION = 0
    MAX_POSITION = 4095
    CENTER_POSITION = 2048

    # 速度范围
    MIN_SPEED = 0
    MAX_SPEED = 2047

    # 加速度范围
    MIN_ACCELERATION = 0
    MAX_ACCELERATION = 255

    # 扭矩范围
    MIN_TORQUE = 0
    MAX_TORQUE = 2047

    # 温度范围
    MIN_TEMPERATURE = 0
    MAX_TEMPERATURE = 100
    DEFAULT_TEMP_LIMIT = 80

    # 电压范围 (0.1V单位)
    MIN_VOLTAGE = 50  # 5.0V
    MAX_VOLTAGE = 150  # 15.0V
    DEFAULT_VOLTAGE_MIN = 60   # 6.0V
    DEFAULT_VOLTAGE_MAX = 140  # 14.0V


class PIDConfig:
    """PID控制配置"""

    # PID参数范围
    MIN_PID_GAIN = 0
    MAX_PID_GAIN = 255

    # 默认PID参数
    DEFAULT_POSITION_PID = {
        'P': 32,
        'I': 0,
        'D': 32
    }

    DEFAULT_SPEED_PID = {
        'P': 10,
        'I': 200
    }

    # 启动扭矩配置
    DEFAULT_STARTUP_TORQUE = 16
    MIN_STARTUP_TORQUE = 0
    MAX_STARTUP_TORQUE = 255


class SafetyConfig:
    """安全配置"""

    # 保护参数默认值
    DEFAULT_OVERLOAD_CURRENT = 500
    DEFAULT_OVERLOAD_TIME = 200
    DEFAULT_OVERCURRENT_TIME = 200
    DEFAULT_PROTECTION_TORQUE = 20
    DEFAULT_OVERLOAD_TORQUE = 80

    # 死区配置
    DEFAULT_DEAD_ZONE = 1
    MIN_DEAD_ZONE = 0
    MAX_DEAD_ZONE = 127

    # 角度分辨率
    DEFAULT_ANGLE_RESOLUTION = 1
    MIN_ANGLE_RESOLUTION = 1
    MAX_ANGLE_RESOLUTION = 255


class SystemConfig:
    """系统配置"""

    # 扫描配置
    DEFAULT_SCAN_RANGE = (1, 20)
    MAX_SCAN_RANGE = (1, 253)

    # 超时配置
    DEFAULT_TIMEOUT = 1000  # ms
    PING_TIMEOUT = 500      # ms
    READ_TIMEOUT = 1000     # ms
    WRITE_TIMEOUT = 1000    # ms

    # 重试配置
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 0.1  # seconds

    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'ftservo.log'

    # UI配置
    UI_UPDATE_INTERVAL = 100  # ms
    MAX_SERVO_DISPLAY = 16
    WINDOW_SIZE = (1200, 800)


class UserInterfaceConfig:
    """用户界面配置"""

    # 颜色主题
    COLORS = {
        'bg_primary': '#2b2b2b',
        'bg_secondary': '#3c3c3c',
        'text_primary': '#ffffff',
        'text_secondary': '#cccccc',
        'accent': '#007acc',
        'success': '#4caf50',
        'warning': '#ff9800',
        'error': '#f44336',
        'normal': '#2196f3'
    }

    # 状态颜色映射
    STATUS_COLORS = {
        'normal': COLORS['success'],
        'warning': COLORS['warning'],
        'error': COLORS['error'],
        'unknown': COLORS['text_secondary']
    }

    # 字体配置
    FONTS = {
        'default': ('Arial', 10),
        'title': ('Arial', 12, 'bold'),
        'monospace': ('Consolas', 9)
    }


class ErrorCodes:
    """错误代码定义"""

    # 通信错误
    COMM_SUCCESS = 0
    COMM_PORT_BUSY = -1
    COMM_TX_FAIL = -2
    COMM_RX_FAIL = -3
    COMM_RX_TIMEOUT = -4
    COMM_RX_CORRUPT = -5

    # 硬件错误
    ERRBIT_VOLTAGE = 1
    ERRBIT_ANGLE = 2
    ERRBIT_OVERHEAT = 4
    ERRBIT_OVERLOAD = 8
    ERRBIT_OVERELE = 16
    ERRBIT_OVERCURRENT = 32

    # 应用错误
    ERROR_SERVO_NOT_FOUND = -100
    ERROR_INVALID_PARAMETER = -101
    ERROR_OPERATION_FAILED = -102
    ERROR_PERMISSION_DENIED = -103


class LogLevel:
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# 全局配置实例
communication = CommunicationConfig()
servo = ServoConfig()
pid = PIDConfig()
safety = SafetyConfig()
system = SystemConfig()
ui = UserInterfaceConfig()
errors = ErrorCodes()
log_level = LogLevel()