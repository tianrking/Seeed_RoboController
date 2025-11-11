#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo PID Controller Module
PID控制模块 - 基于逆向工程发现的PID参数调节功能
"""

from typing import List, Optional, Tuple, Dict, Any
from ..config.memory_map import MemoryMap
from ..config.settings import PIDConfig, ErrorCodes
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class PIDController:
    """PID控制器"""

    def __init__(self, connection_manager):
        """
        初始化PID控制器

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.PIDController")

    def read_position_pid(self, servo_id: int) -> Tuple[Optional[List[int]], int, Optional[str]]:
        """
        读取位置PID参数 (使用逆向发现的地址21-23)

        Args:
            servo_id: 舵机ID

        Returns:
            (pid_params, result, error)
        """
        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)

            # 读取PID参数
            p_data, p_result, p_error = self.connection.read_memory(servo_id, MemoryMap.POSITION_P_GAIN, 1)
            i_data, i_result, i_error = self.connection.read_memory(servo_id, MemoryMap.POSITION_I_GAIN, 1)
            d_data, d_result, d_error = self.connection.read_memory(servo_id, MemoryMap.POSITION_D_GAIN, 1)

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if (p_result == 0 and i_result == 0 and d_result == 0 and
                p_data and i_data and d_data):

                pid_params = [
                    DataParser.bytes_to_int(p_data),  # P增益
                    DataParser.bytes_to_int(i_data),  # I增益
                    DataParser.bytes_to_int(d_data)   # D增益
                ]
                return pid_params, 0, None

            return None, -1, "读取PID参数失败"

        except Exception as e:
            self.logger.error(f"读取位置PID参数失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def write_position_pid(self, servo_id: int, p_gain: int, i_gain: int, d_gain: int) -> Tuple[int, Optional[str]]:
        """
        写入位置PID参数 (使用逆向发现的地址21-23)

        Args:
            servo_id: 舵机ID
            p_gain: P增益 (0-255)
            i_gain: I增益 (0-255)
            d_gain: D增益 (0-255)

        Returns:
            (result, error)
        """
        # 参数验证
        if not (PIDConfig.MIN_PID_GAIN <= p_gain <= PIDConfig.MAX_PID_GAIN):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"P增益超出范围: {p_gain}"
        if not (PIDConfig.MIN_PID_GAIN <= i_gain <= PIDConfig.MAX_PID_GAIN):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"I增益超出范围: {i_gain}"
        if not (PIDConfig.MIN_PID_GAIN <= d_gain <= PIDConfig.MAX_PID_GAIN):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"D增益超出范围: {d_gain}"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入PID参数
            p_result, p_error = self.connection.write_memory(servo_id, MemoryMap.POSITION_P_GAIN, 1, [p_gain])
            if p_result != 0:
                return p_result, p_error

            i_result, i_error = self.connection.write_memory(servo_id, MemoryMap.POSITION_I_GAIN, 1, [i_gain])
            if i_result != 0:
                return i_result, i_error

            d_result, d_error = self.connection.write_memory(servo_id, MemoryMap.POSITION_D_GAIN, 1, [d_gain])
            if d_result != 0:
                return d_result, d_error

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            self.logger.info(f"位置PID参数设置成功 ID:{servo_id}, P:{p_gain}, I:{i_gain}, D:{d_gain}")
            return 0, None

        except Exception as e:
            self.logger.error(f"写入位置PID参数失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_speed_pid(self, servo_id: int) -> Tuple[Optional[List[int]], int, Optional[str]]:
        """
        读取速度PID参数 (使用逆向发现的地址37, 39)

        Args:
            servo_id: 舵机ID

        Returns:
            (pid_params, result, error)
        """
        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)

            # 读取速度PID参数
            p_data, p_result, p_error = self.connection.read_memory(servo_id, MemoryMap.SPEED_P_GAIN, 1)
            i_data, i_result, i_error = self.connection.read_memory(servo_id, MemoryMap.SPEED_I_GAIN_L, 2)

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if (p_result == 0 and i_result == 0 and
                p_data and i_data and len(i_data) >= 2):

                p_gain = DataParser.bytes_to_int(p_data)
                i_gain = DataParser.bytes_to_int(i_data[:2], signed=True)

                pid_params = [p_gain, i_gain]
                return pid_params, 0, None

            return None, -1, "读取速度PID参数失败"

        except Exception as e:
            self.logger.error(f"读取速度PID参数失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def write_speed_pid(self, servo_id: int, p_gain: int, i_gain: int) -> Tuple[int, Optional[str]]:
        """
        写入速度PID参数 (使用逆向发现的地址37, 39)

        Args:
            servo_id: 舵机ID
            p_gain: P增益 (0-255)
            i_gain: I增益 (-32768 到 32767)

        Returns:
            (result, error)
        """
        # 参数验证
        if not (PIDConfig.MIN_PID_GAIN <= p_gain <= PIDConfig.MAX_PID_GAIN):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"P增益超出范围: {p_gain}"
        if not (-32768 <= i_gain <= 32767):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"I增益超出范围: {i_gain}"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入速度PID参数
            p_result, p_error = self.connection.write_memory(servo_id, MemoryMap.SPEED_P_GAIN, 1, [p_gain])
            if p_result != 0:
                return p_result, p_error

            i_data = DataParser.int_to_bytes(i_gain, 2, signed=True)
            i_result, i_error = self.connection.write_memory(servo_id, MemoryMap.SPEED_I_GAIN_L, 2, i_data)
            if i_result != 0:
                return i_result, i_error

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            self.logger.info(f"速度PID参数设置成功 ID:{servo_id}, P:{p_gain}, I:{i_gain}")
            return 0, None

        except Exception as e:
            self.logger.error(f"写入速度PID参数失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_startup_torque(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取启动扭矩 (使用逆向发现的地址24)

        Args:
            servo_id: 舵机ID

        Returns:
            (startup_torque, result, error)
        """
        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)

            # 读取启动扭矩
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.STARTUP_TORQUE, 1)

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if result == 0 and data and len(data) > 0:
                startup_torque = DataParser.bytes_to_int(data)
                return startup_torque, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取启动扭矩失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def write_startup_torque(self, servo_id: int, startup_torque: int) -> Tuple[int, Optional[str]]:
        """
        写入启动扭矩 (使用逆向发现的地址24)

        Args:
            servo_id: 舵机ID
            startup_torque: 启动扭矩 (0-255)

        Returns:
            (result, error)
        """
        # 参数验证
        if not (PIDConfig.MIN_STARTUP_TORQUE <= startup_torque <= PIDConfig.MAX_STARTUP_TORQUE):
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"启动扭矩超出范围: {startup_torque}"

        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return unlock_result, unlock_error

            # 写入启动扭矩
            result, error = self.connection.write_memory(servo_id, MemoryMap.STARTUP_TORQUE, 1, [startup_torque])

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if result == 0:
                self.logger.info(f"启动扭矩设置成功 ID:{servo_id}, 扭矩:{startup_torque}")

            return result, error

        except Exception as e:
            self.logger.error(f"写入启动扭矩失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def set_pid_params(self, servo_id: int,
                      position_pid: Optional[List[int]] = None,
                      speed_pid: Optional[List[int]] = None,
                      startup_torque: Optional[int] = None) -> bool:
        """
        综合设置PID参数

        Args:
            servo_id: 舵机ID
            position_pid: 位置PID参数 [P, I, D]
            speed_pid: 速度PID参数 [P, I]
            startup_torque: 启动扭矩

        Returns:
            设置是否成功
        """
        success = True

        # 设置位置PID
        if position_pid and len(position_pid) == 3:
            result, error = self.write_position_pid(servo_id, position_pid[0], position_pid[1], position_pid[2])
            if result != 0:
                self.logger.error(f"设置位置PID失败: {error}")
                success = False

        # 设置速度PID
        if speed_pid and len(speed_pid) == 2:
            result, error = self.write_speed_pid(servo_id, speed_pid[0], speed_pid[1])
            if result != 0:
                self.logger.error(f"设置速度PID失败: {error}")
                success = False

        # 设置启动扭矩
        if startup_torque is not None:
            result, error = self.write_startup_torque(servo_id, startup_torque)
            if result != 0:
                self.logger.error(f"设置启动扭矩失败: {error}")
                success = False

        return success

    def get_pid_summary(self, servo_id: int) -> Dict[str, Any]:
        """
        获取PID参数摘要

        Args:
            servo_id: 舵机ID

        Returns:
            PID参数摘要字典
        """
        summary = {
            'servo_id': servo_id,
            'position_pid': None,
            'speed_pid': None,
            'startup_torque': None,
            'error': None
        }

        try:
            # 读取位置PID
            position_pid, result, error = self.read_position_pid(servo_id)
            if result == 0:
                summary['position_pid'] = {
                    'P': position_pid[0],
                    'I': position_pid[1],
                    'D': position_pid[2]
                }

            # 读取速度PID
            speed_pid, result, error = self.read_speed_pid(servo_id)
            if result == 0:
                summary['speed_pid'] = {
                    'P': speed_pid[0],
                    'I': speed_pid[1]
                }

            # 读取启动扭矩
            startup_torque, result, error = self.read_startup_torque(servo_id)
            if result == 0:
                summary['startup_torque'] = startup_torque

        except Exception as e:
            self.logger.error(f"获取PID摘要失败 ID:{servo_id}, 错误: {e}")
            summary['error'] = str(e)

        return summary

    def reset_pid_to_default(self, servo_id: int) -> bool:
        """
        重置PID参数为默认值

        Args:
            servo_id: 舵机ID

        Returns:
            重置是否成功
        """
        return self.set_pid_params(
            servo_id,
            position_pid=PIDConfig.DEFAULT_POSITION_PID,
            speed_pid=PIDConfig.DEFAULT_SPEED_PID,
            startup_torque=PIDConfig.DEFAULT_STARTUP_TORQUE
        )