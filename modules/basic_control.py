#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Basic Control Module
基础控制模块 - 提供舵机的基本运动控制功能
"""

import time
from typing import List, Tuple, Optional, Dict, Any
from ..config.memory_map import MemoryMap
from ..config.settings import ServoConfig, ErrorCodes
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class BasicControl:
    """基础控制器"""

    def __init__(self, connection_manager):
        """
        初始化基础控制器

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.BasicControl")

    def write_position(self, servo_id: int, position: int, speed: int = 0, acceleration: int = 0) -> Tuple[int, Optional[str]]:
        """
        写入位置控制

        Args:
            servo_id: 舵机ID
            position: 目标位置 (0-4095)
            speed: 运动速度 (0-2047)
            acceleration: 加速度 (0-255)

        Returns:
            (result, error)
        """
        # 参数验证
        if not ServoConfig.MIN_POSITION <= position <= ServoConfig.MAX_POSITION:
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"位置超出范围: {position}"

        if not ServoConfig.MIN_SPEED <= speed <= ServoConfig.MAX_SPEED:
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"速度超出范围: {speed}"

        if not ServoConfig.MIN_ACCELERATION <= acceleration <= ServoConfig.MAX_ACCELERATION:
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"加速度超出范围: {acceleration}"

        try:
            # 使用SDK的WritePosEx方法
            if hasattr(self.connection.protocol_handler, 'WritePosEx'):
                torque = ServoConfig.MAX_TORQUE  # 默认最大扭矩
                result, error = self.connection.protocol_handler.WritePosEx(
                    servo_id, position, speed, acceleration, torque
                )
                return result, error
            else:
                # 回退到直接内存写入
                position_data = DataParser.int_to_bytes(position, 2)
                return self.connection.write_memory(servo_id, MemoryMap.GOAL_POSITION_L, 2, position_data)

        except Exception as e:
            self.logger.error(f"写入位置失败 ID:{servo_id}, 位置:{position}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_position(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取当前位置

        Args:
            servo_id: 舵机ID

        Returns:
            (position, result, error)
        """
        try:
            if hasattr(self.connection.protocol_handler, 'ReadPos'):
                position, result, error = self.connection.protocol_handler.ReadPos(servo_id)
                return position, result, error
            else:
                # 直接读取内存
                data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_POSITION_L, 2)
                if result == ErrorCodes.COMM_SUCCESS and data:
                    position = DataParser.parse_position(data)
                    return position, result, error
                return None, result, error

        except Exception as e:
            self.logger.error(f"读取位置失败 ID:{servo_id}, 错误: {e}")
            return None, ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def write_speed(self, servo_id: int, speed: int) -> Tuple[int, Optional[str]]:
        """
        写入速度控制

        Args:
            servo_id: 舵机ID
            speed: 目标速度 (-2047 到 2047)

        Returns:
            (result, error)
        """
        # 参数验证
        speed_abs = abs(speed)
        if speed_abs > ServoConfig.MAX_SPEED:
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"速度超出范围: {speed}"

        try:
            speed_data = DataParser.int_to_bytes(speed, 2, signed=True)
            return self.connection.write_memory(servo_id, MemoryMap.GOAL_SPEED_L, 2, speed_data)

        except Exception as e:
            self.logger.error(f"写入速度失败 ID:{servo_id}, 速度:{speed}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_speed(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取当前速度

        Args:
            servo_id: 舵机ID

        Returns:
            (speed, result, error)
        """
        try:
            if hasattr(self.connection.protocol_handler, 'ReadSpeed'):
                speed, result, error = self.connection.protocol_handler.ReadSpeed(servo_id)
                return speed, result, error
            else:
                # 直接读取内存
                data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_SPEED_L, 2)
                if result == ErrorCodes.COMM_SUCCESS and data:
                    speed = DataParser.parse_speed(data)
                    return speed, result, error
                return None, result, error

        except Exception as e:
            self.logger.error(f"读取速度失败 ID:{servo_id}, 错误: {e}")
            return None, ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def enable_torque(self, servo_id: int, enable: bool = True) -> Tuple[int, Optional[str]]:
        """
        使能/禁用扭矩

        Args:
            servo_id: 舵机ID
            enable: 是否使能扭矩

        Returns:
            (result, error)
        """
        try:
            torque_value = 1 if enable else 0
            return self.connection.write_memory(servo_id, MemoryMap.TORQUE_ENABLE, 1, [torque_value])

        except Exception as e:
            self.logger.error(f"设置扭矩使能失败 ID:{servo_id}, 使能:{enable}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def set_torque_limit(self, servo_id: int, torque_limit: int) -> Tuple[int, Optional[str]]:
        """
        设置扭矩限制

        Args:
            servo_id: 舵机ID
            torque_limit: 扭矩限制 (0-2047)

        Returns:
            (result, error)
        """
        if not ServoConfig.MIN_TORQUE <= torque_limit <= ServoConfig.MAX_TORQUE:
            return ErrorCodes.ERROR_INVALID_PARAMETER, f"扭矩限制超出范围: {torque_limit}"

        try:
            torque_data = DataParser.int_to_bytes(torque_limit, 2)
            return self.connection.write_memory(servo_id, MemoryMap.TORQUE_LIMIT_L, 2, torque_data)

        except Exception as e:
            self.logger.error(f"设置扭矩限制失败 ID:{servo_id}, 限制:{torque_limit}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def move_to_position(self, servo_id: int, position: int, speed: int = 100, acceleration: int = 50, timeout: float = 5.0) -> bool:
        """
        移动到指定位置并等待完成

        Args:
            servo_id: 舵机ID
            position: 目标位置
            speed: 运动速度
            acceleration: 加速度
            timeout: 超时时间(秒)

        Returns:
            是否成功到达目标位置
        """
        # 发送位置命令
        result, error = self.write_position(servo_id, position, speed, acceleration)
        if result != ErrorCodes.COMM_SUCCESS:
            self.logger.error(f"发送位置命令失败: {error}")
            return False

        # 等待运动完成
        start_time = time.time()
        tolerance = 10  # 位置容差

        while time.time() - start_time < timeout:
            current_pos, result, error = self.read_position(servo_id)
            if result == ErrorCodes.COMM_SUCCESS:
                if abs(current_pos - position) <= tolerance:
                    self.logger.info(f"舵机 {servo_id} 到达目标位置 {position}")
                    return True

            time.sleep(0.05)

        self.logger.warning(f"舵机 {servo_id} 移动超时")
        return False

    def stop_servo(self, servo_id: int) -> Tuple[int, Optional[str]]:
        """
        停止舵机运动

        Args:
            servo_id: 舵机ID

        Returns:
            (result, error)
        """
        try:
            # 读取当前位置
            current_pos, result, error = self.read_position(servo_id)
            if result != ErrorCodes.COMM_SUCCESS:
                return result, error

            # 设置当前位置为目标位置
            return self.write_position(servo_id, current_pos, 0, 0)

        except Exception as e:
            self.logger.error(f"停止舵机失败 ID:{servo_id}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def get_servo_status(self, servo_id: int) -> Dict[str, Any]:
        """
        获取舵机完整状态

        Args:
            servo_id: 舵机ID

        Returns:
            舵机状态字典
        """
        status = {
            'id': servo_id,
            'connected': False,
            'position': None,
            'speed': None,
            'voltage': None,
            'temperature': None,
            'moving': False,
            'error': None
        }

        try:
            # 检查连接
            model_number, result, error = self.connection.ping(servo_id)
            if result != ErrorCodes.COMM_SUCCESS:
                status['error'] = error
                return status

            status['connected'] = True
            status['model_number'] = model_number

            # 读取位置
            position, result, error = self.read_position(servo_id)
            if result == ErrorCodes.COMM_SUCCESS:
                status['position'] = position

            # 读取速度
            speed, result, error = self.read_speed(servo_id)
            if result == ErrorCodes.COMM_SUCCESS:
                status['speed'] = speed

            # 读取电压
            voltage_data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_VOLTAGE, 1)
            if result == ErrorCodes.COMM_SUCCESS and voltage_data:
                status['voltage'] = DataParser.parse_voltage(voltage_data)

            # 读取温度
            temp_data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_TEMPERATURE, 1)
            if result == ErrorCodes.COMM_SUCCESS and temp_data:
                status['temperature'] = DataParser.parse_temperature(temp_data)

            # 读取运动状态
            moving_data, result, error = self.connection.read_memory(servo_id, MemoryMap.MOVING_STATUS, 1)
            if result == ErrorCodes.COMM_SUCCESS and moving_data:
                status['moving'] = bool(moving_data[0])

        except Exception as e:
            self.logger.error(f"获取舵机状态失败 ID:{servo_id}, 错误: {e}")
            status['error'] = str(e)

        return status

    def multi_servo_control(self, servo_configs: List[Dict[str, Any]]) -> Dict[int, Tuple[int, Optional[str]]]:
        """
        多舵机同步控制

        Args:
            servo_configs: 舵机配置列表，每个配置包含 'id', 'position', 'speed', 'acceleration'

        Returns:
            每个舵机的操作结果
        """
        results = {}

        for config in servo_configs:
            servo_id = config['id']
            position = config.get('position', ServoConfig.CENTER_POSITION)
            speed = config.get('speed', 100)
            acceleration = config.get('acceleration', 50)

            result, error = self.write_position(servo_id, position, speed, acceleration)
            results[servo_id] = (result, error)

        return results