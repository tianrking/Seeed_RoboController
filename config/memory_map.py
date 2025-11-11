#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Memory Map Definition
基于逆向工程分析的完整内存映射定义
"""

class MemoryMap:
    """FTServo内存映射定义"""

    # ==================== EPROM区域 - 固件信息 (只读) ====================
    FIRMWARE_MAJOR_VERSION = 0
    FIRMWARE_MINOR_VERSION = 1
    SERVO_MAJOR_VERSION = 3
    SERVO_MINOR_VERSION = 4

    # ==================== EPROM区域 - 基本配置 (读写) ====================
    ID = 5
    BAUD_RATE = 6
    RESERVED = 7
    STATUS_RETURN_LEVEL = 8

    # ==================== EPROM区域 - 运动限制 (读写) ====================
    MIN_POSITION_LIMIT_L = 9
    MIN_POSITION_LIMIT_H = 10
    MAX_POSITION_LIMIT_L = 11
    MAX_POSITION_LIMIT_H = 12
    MAX_TEMPERATURE_LIMIT = 13
    MAX_INPUT_VOLTAGE = 14
    MIN_INPUT_VOLTAGE = 15
    MAX_TORQUE_LIMIT_L = 16
    MAX_TORQUE_LIMIT_H = 17

    # ==================== EPROM区域 - 高级控制 (读写) ====================
    SETUP_BYTE = 18
    PROTECTION_SWITCH = 19
    LED_ALARM_CONDITION = 20

    # PID控制参数 (逆向发现)
    POSITION_P_GAIN = 21
    POSITION_D_GAIN = 22
    POSITION_I_GAIN = 23
    STARTUP_TORQUE = 24
    MAX_CURRENT_L = 25
    MAX_CURRENT_H = 26
    CW_DEAD_ZONE = 27
    CCW_DEAD_ZONE = 28
    OVERLOAD_CURRENT_L = 29
    OVERLOAD_CURRENT_H = 30
    ANGLE_RESOLUTION = 31
    POSITION_OFFSET_L = 32
    POSITION_OFFSET_H = 33
    WORK_MODE = 34
    PROTECTION_TORQUE_L = 35
    PROTECTION_TORQUE_H = 36
    OVERLOAD_PROTECTION_TIME_L = 37
    OVERLOAD_PROTECTION_TIME_H = 38
    OVERLOAD_TORQUE_L = 39
    OVERLOAD_TORQUE_H = 40
    SPEED_P_GAIN = 41
    OVERCURRENT_PROTECTION_TIME_L = 42
    OVERCURRENT_PROTECTION_TIME_H = 43
    SPEED_I_GAIN_L = 44
    SPEED_I_GAIN_H = 45

    # ==================== SRAM区域 - 实时控制 (读写) ====================
    TORQUE_ENABLE = 46
    TARGET_ACCELERATION = 47
    GOAL_POSITION_L = 48
    GOAL_POSITION_H = 49
    GOAL_PWM_L = 50
    GOAL_PWM_H = 51
    GOAL_SPEED_L = 52
    GOAL_SPEED_H = 53
    TORQUE_LIMIT_L = 54
    TORQUE_LIMIT_H = 55
    LOCK = 56

    # ==================== SRAM区域 - 状态反馈 (只读) ====================
    PRESENT_POSITION_L = 57
    PRESENT_POSITION_H = 58
    PRESENT_SPEED_L = 59
    PRESENT_SPEED_H = 60
    PRESENT_PWM_L = 61
    PRESENT_PWM_H = 62
    PRESENT_VOLTAGE = 63
    PRESENT_TEMPERATURE = 64
    SYNC_WRITE_FLAG = 65
    HARDWARE_ERROR_STATUS = 66
    MOVING_STATUS = 67
    PRESENT_CURRENT_L = 68
    PRESENT_CURRENT_H = 69

    # ==================== 默认参数区域 (系统级) ====================
    MOTION_THRESHOLD = 80
    DT_S = 81
    V_K = 82
    V_MIN = 83
    V_MAX = 84
    A_MAX = 85
    K_ACC = 86


class MemoryRegions:
    """内存区域定义"""

    EPROM_READONLY = {
        'start': 0,
        'end': 4,
        'description': '固件信息区域 - 只读'
    }

    EPROM_CONFIG = {
        'start': 5,
        'end': 17,
        'description': '基本配置区域 - 读写'
    }

    EPROM_PID = {
        'start': 21,
        'end': 45,
        'description': 'PID控制参数区域 - 读写'
    }

    SRAM_CONTROL = {
        'start': 46,
        'end': 56,
        'description': '实时控制区域 - 读写'
    }

    SRAM_STATUS = {
        'start': 57,
        'end': 69,
        'description': '状态反馈区域 - 只读'
    }

    DEFAULT_PARAMS = {
        'start': 80,
        'end': 86,
        'description': '默认参数区域 - 系统级'
    }


class AddressNames:
    """内存地址名称映射"""

    NAMES = {
        0: 'FIRMWARE_MAJOR_VERSION',
        1: 'FIRMWARE_MINOR_VERSION',
        3: 'SERVO_MAJOR_VERSION',
        4: 'SERVO_MINOR_VERSION',
        5: 'ID',
        6: 'BAUD_RATE',
        7: 'RESERVED',
        8: 'STATUS_RETURN_LEVEL',
        9: 'MIN_POSITION_LIMIT_L',
        10: 'MIN_POSITION_LIMIT_H',
        11: 'MAX_POSITION_LIMIT_L',
        12: 'MAX_POSITION_LIMIT_H',
        13: 'MAX_TEMPERATURE_LIMIT',
        14: 'MAX_INPUT_VOLTAGE',
        15: 'MIN_INPUT_VOLTAGE',
        16: 'MAX_TORQUE_LIMIT_L',
        17: 'MAX_TORQUE_LIMIT_H',
        18: 'SETUP_BYTE',
        19: 'PROTECTION_SWITCH',
        20: 'LED_ALARM_CONDITION',
        21: 'POSITION_P_GAIN',
        22: 'POSITION_D_GAIN',
        23: 'POSITION_I_GAIN',
        24: 'STARTUP_TORQUE',
        25: 'MAX_CURRENT_L',
        26: 'MAX_CURRENT_H',
        27: 'CW_DEAD_ZONE',
        28: 'CCW_DEAD_ZONE',
        29: 'OVERLOAD_CURRENT_L',
        30: 'OVERLOAD_CURRENT_H',
        31: 'ANGLE_RESOLUTION',
        32: 'POSITION_OFFSET_L',
        33: 'POSITION_OFFSET_H',
        34: 'WORK_MODE',
        35: 'PROTECTION_TORQUE_L',
        36: 'PROTECTION_TORQUE_H',
        37: 'OVERLOAD_PROTECTION_TIME_L',
        38: 'OVERLOAD_PROTECTION_TIME_H',
        39: 'OVERLOAD_TORQUE_L',
        40: 'OVERLOAD_TORQUE_H',
        41: 'SPEED_P_GAIN',
        42: 'OVERCURRENT_PROTECTION_TIME_L',
        43: 'OVERCURRENT_PROTECTION_TIME_H',
        44: 'SPEED_I_GAIN_L',
        45: 'SPEED_I_GAIN_H',
        46: 'TORQUE_ENABLE',
        47: 'TARGET_ACCELERATION',
        48: 'GOAL_POSITION_L',
        49: 'GOAL_POSITION_H',
        50: 'GOAL_PWM_L',
        51: 'GOAL_PWM_H',
        52: 'GOAL_SPEED_L',
        53: 'GOAL_SPEED_H',
        54: 'TORQUE_LIMIT_L',
        55: 'TORQUE_LIMIT_H',
        56: 'LOCK',
        57: 'PRESENT_POSITION_L',
        58: 'PRESENT_POSITION_H',
        59: 'PRESENT_SPEED_L',
        60: 'PRESENT_SPEED_H',
        61: 'PRESENT_PWM_L',
        62: 'PRESENT_PWM_H',
        63: 'PRESENT_VOLTAGE',
        64: 'PRESENT_TEMPERATURE',
        65: 'SYNC_WRITE_FLAG',
        66: 'HARDWARE_ERROR_STATUS',
        67: 'MOVING_STATUS',
        68: 'PRESENT_CURRENT_L',
        69: 'PRESENT_CURRENT_H',
        80: 'MOTION_THRESHOLD',
        81: 'DT_S',
        82: 'V_K',
        83: 'V_MIN',
        84: 'V_MAX',
        85: 'A_MAX',
        86: 'K_ACC'
    }

    @classmethod
    def get_name(cls, address):
        """获取地址名称"""
        return cls.NAMES.get(address, f'UNKNOWN_{address}')

    @classmethod
    def get_address(cls, name):
        """根据名称获取地址"""
        for addr, addr_name in cls.NAMES.items():
            if addr_name == name:
                return addr
        return None