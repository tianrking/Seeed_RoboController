#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Hardware Configuration Module
硬件配置模块 - 基于逆向工程发现的硬件配置功能
"""

from typing import Optional, Tuple, Dict, Any
from ..config.memory_map import MemoryMap
from ..config.settings import ServoConfig, SafetyConfig, ErrorCodes
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class HardwareConfig:
    """硬件配置器"""

    def __init__(self, connection_manager):
        """
        初始化硬件配置器

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.HardwareConfig")

    def set_servo_id(self, current_id: int, new_id: int) -> Tuple[int, Optional[str]]:
        """
        设置舵机ID

        Args:
            current_id: 当前舵机ID
            new_id: 新舵机ID (1-253)

        Returns:
            (result, error)
        """
        if not (1 <= new_id <= 253):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"新ID超出范围: {new_id}"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(current_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入新ID
            result, error = self.connection.write_memory(current_id, MemoryMap.ID, 1, [new_id])

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(current_id)

            if result == 0:
                self.logger.info(f"舵机ID设置成功: {current_id} -> {new_id}")

            return result, error

        except Exception as e:
            self.logger.error(f"设置舵机ID失败: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_servo_id(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取舵机ID

        Args:
            servo_id: 舵机ID

        Returns:
            (servo_id, result, error)
        """
        try:
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.ID, 1)
            if result == 0 and data and len(data) > 0:
                return DataParser.bytes_to_int(data), result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取舵机ID失败: {e}")
            return None, -1, str(e)