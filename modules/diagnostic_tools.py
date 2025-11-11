#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Diagnostic Tools Module
诊断工具模块 - 基于逆向工程发现的高级诊断功能
"""

import time
from typing import Dict, Any, Optional
from ..config.memory_map import MemoryMap
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class DiagnosticTools:
    """诊断工具"""

    def __init__(self, connection_manager):
        """
        初始化诊断工具

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.DiagnosticTools")

    def get_firmware_version(self, servo_id: int) -> Dict[str, Any]:
        """
        获取固件版本信息 (使用逆向发现的地址0-1, 3-4)

        Args:
            servo_id: 舵机ID

        Returns:
            固件版本信息字典
        """
        version_info = {
            'servo_id': servo_id,
            'firmware_major': None,
            'firmware_minor': None,
            'hardware_major': None,
            'hardware_minor': None,
            'error': None
        }

        try:
            # 读取固件版本
            fw_major_data, result, error = self.connection.read_memory(servo_id, MemoryMap.FIRMWARE_MAJOR_VERSION, 1)
            if result == 0 and fw_major_data:
                version_info['firmware_major'] = DataParser.bytes_to_int(fw_major_data)

            fw_minor_data, result, error = self.connection.read_memory(servo_id, MemoryMap.FIRMWARE_MINOR_VERSION, 1)
            if result == 0 and fw_minor_data:
                version_info['firmware_minor'] = DataParser.bytes_to_int(fw_minor_data)

            # 读取硬件版本
            hw_major_data, result, error = self.connection.read_memory(servo_id, MemoryMap.SERVO_MAJOR_VERSION, 1)
            if result == 0 and hw_major_data:
                version_info['hardware_major'] = DataParser.bytes_to_int(hw_major_data)

            hw_minor_data, result, error = self.connection.read_memory(servo_id, MemoryMap.SERVO_MINOR_VERSION, 1)
            if result == 0 and hw_minor_data:
                version_info['hardware_minor'] = DataParser.bytes_to_int(hw_minor_data)

        except Exception as e:
            self.logger.error(f"获取固件版本失败 ID:{servo_id}, 错误: {e}")
            version_info['error'] = str(e)

        return version_info

    def get_full_diagnostics(self, servo_id: int) -> Dict[str, Any]:
        """
        获取完整诊断信息

        Args:
            servo_id: 舵机ID

        Returns:
            完整诊断信息字典
        """
        diagnostics = {
            'servo_id': servo_id,
            'timestamp': time.time(),
            'firmware_version': self.get_firmware_version(servo_id),
            'memory_status': {},
            'hardware_status': {},
            'performance_metrics': {},
            'errors': []
        }

        try:
            # 基础连接测试
            model_number, result, error = self.connection.ping(servo_id)
            if result != 0:
                diagnostics['errors'].append(f"连接失败: {error}")
                return diagnostics

            # 读取关键状态寄存器
            key_addresses = [
                (MemoryMap.PRESENT_POSITION_L, 2, "当前位置"),
                (MemoryMap.PRESENT_SPEED_L, 2, "当前速度"),
                (MemoryMap.PRESENT_VOLTAGE, 1, "当前电压"),
                (MemoryMap.PRESENT_TEMPERATURE, 1, "当前温度"),
                (MemoryMap.PRESENT_CURRENT_L, 2, "当前电流"),
                (MemoryMap.HARDWARE_ERROR_STATUS, 1, "硬件错误状态"),
                (MemoryMap.MOVING_STATUS, 1, "运动状态")
            ]

            for addr, length, name in key_addresses:
                try:
                    data, result, error = self.connection.read_memory(servo_id, addr, length)
                    if result == 0 and data:
                        if length == 1:
                            value = DataParser.bytes_to_int(data)
                        else:
                            value = DataParser.bytes_to_int(data, signed=True)
                        diagnostics['hardware_status'][name] = value
                    else:
                        diagnostics['errors'].append(f"读取{name}失败: {error}")
                except Exception as e:
                    diagnostics['errors'].append(f"读取{name}异常: {e}")

        except Exception as e:
            self.logger.error(f"获取完整诊断失败 ID:{servo_id}, 错误: {e}")
            diagnostics['errors'].append(f"诊断过程异常: {e}")

        return diagnostics