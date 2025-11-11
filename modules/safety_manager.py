#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Safety Manager Module
安全保护模块 - 基于逆向工程发现的安全配置功能
"""

from typing import Optional, Tuple, Dict, Any
from ..config.memory_map import MemoryMap
from ..config.settings import SafetyConfig, ErrorCodes
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class SafetyManager:
    """安全管理器"""

    def __init__(self, connection_manager):
        """
        初始化安全管理器

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.SafetyManager")

    def configure_temperature_limit(self, servo_id: int, temperature_limit: int) -> Tuple[int, Optional[str]]:
        """
        配置温度限制 (使用逆向发现的地址13)

        Args:
            servo_id: 舵机ID
            temperature_limit: 温度限制 (°C)

        Returns:
            (result, error)
        """
        if not (0 <= temperature_limit <= 100):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"温度限制超出范围: {temperature_limit}"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入温度限制
            result, error = self.connection.write_memory(servo_id, MemoryMap.MAX_TEMPERATURE_LIMIT, 1, [temperature_limit])

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if result == 0:
                self.logger.info(f"温度限制设置成功 ID:{servo_id}, 限制:{temperature_limit}°C")

            return result, error

        except Exception as e:
            self.logger.error(f"设置温度限制失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def configure_voltage_limits(self, servo_id: int, min_voltage: float, max_voltage: float) -> Tuple[int, Optional[str]]:
        """
        配置电压限制 (使用逆向发现的地址14-15)

        Args:
            servo_id: 舵机ID
            min_voltage: 最小电压 (V)
            max_voltage: 最大电压 (V)

        Returns:
            (result, error)
        """
        # 转换为0.1V单位
        min_voltage_10 = int(min_voltage * 10)
        max_voltage_10 = int(max_voltage * 10)

        if not (50 <= min_voltage_10 <= 250):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"最小电压超出范围: {min_voltage}V"
        if not (50 <= max_voltage_10 <= 250):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"最大电压超出范围: {max_voltage}V"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入电压限制
            result1, error1 = self.connection.write_memory(servo_id, MemoryMap.MAX_INPUT_VOLTAGE, 1, [max_voltage_10])
            result2, error2 = self.connection.write_memory(servo_id, MemoryMap.MIN_INPUT_VOLTAGE, 1, [min_voltage_10])

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            final_result = result1 if result1 != 0 else result2
            final_error = error1 if result1 != 0 else error2

            if final_result == 0:
                self.logger.info(f"电压限制设置成功 ID:{servo_id}, 范围:{min_voltage}V-{max_voltage}V")

            return final_result, final_error

        except Exception as e:
            self.logger.error(f"设置电压限制失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def configure_safety(self, servo_id: int, temp_limit: Optional[int] = None,
                        voltage_range: Optional[tuple] = None, overload_settings: Optional[Dict] = None) -> bool:
        """
        综合配置安全参数

        Args:
            servo_id: 舵机ID
            temp_limit: 温度限制
            voltage_range: 电压范围 (min_voltage, max_voltage)
            overload_settings: 过载设置字典

        Returns:
            配置是否成功
        """
        success = True

        # 配置温度限制
        if temp_limit is not None:
            result, error = self.configure_temperature_limit(servo_id, temp_limit)
            if result != 0:
                self.logger.error(f"配置温度限制失败: {error}")
                success = False

        # 配置电压限制
        if voltage_range and len(voltage_range) == 2:
            result, error = self.configure_voltage_limits(servo_id, voltage_range[0], voltage_range[1])
            if result != 0:
                self.logger.error(f"配置电压限制失败: {error}")
                success = False

        return success