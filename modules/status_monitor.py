#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Status Monitor Module
状态监控模块 - 基于逆向工程分析的高级监控功能
"""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from ..config.memory_map import MemoryMap
from ..config.settings import ServoConfig, SafetyConfig
from ..utils.logger import get_logger
from ..utils.data_parser import DataParser


class StatusMonitor:
    """状态监控器"""

    def __init__(self, connection_manager):
        """
        初始化状态监控器

        Args:
            connection_manager: 连接管理器实例
        """
        self.connection = connection_manager
        self.logger = get_logger(f"{__name__}.StatusMonitor")

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.monitor_callbacks = []

    def read_temperature(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取舵机温度 (使用逆向发现的地址63)

        Args:
            servo_id: 舵机ID

        Returns:
            (temperature, result, error)
        """
        try:
            # 使用地址63读取温度
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_TEMPERATURE, 1)
            if result == 0 and data and len(data) > 0:
                temperature = DataParser.parse_temperature(data)
                return temperature, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取温度失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def read_temperature_limit(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取温度上限设置 (使用逆向发现的地址13)

        Args:
            servo_id: 舵机ID

        Returns:
            (temperature_limit, result, error)
        """
        try:
            # 解锁EEPROM
            unlock_result, unlock_error = self.connection.protocol_handler.unLockEprom(servo_id)

            # 使用地址13读取温度上限
            data, result, error = self.connection.read_memory(servo_id, 13, 1)

            # 重新锁定EEPROM
            lock_result, lock_error = self.connection.protocol_handler.LockEprom(servo_id)

            if result == 0 and data and len(data) > 0:
                temp_limit = DataParser.parse_temperature(data)
                return temp_limit, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取温度上限失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def read_voltage(self, servo_id: int) -> Tuple[Optional[float], int, Optional[str]]:
        """
        读取电压

        Args:
            servo_id: 舵机ID

        Returns:
            (voltage, result, error)
        """
        try:
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_VOLTAGE, 1)
            if result == 0 and data and len(data) > 0:
                voltage = DataParser.parse_voltage(data)
                return voltage, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取电压失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def read_current(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取电流 (使用逆向发现的地址68-69)

        Args:
            servo_id: 舵机ID

        Returns:
            (current, result, error)
        """
        try:
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.PRESENT_CURRENT_L, 2)
            if result == 0 and data and len(data) >= 2:
                current = DataParser.parse_current(data)
                return current, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取电流失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def read_hardware_error_status(self, servo_id: int) -> Tuple[Optional[int], int, Optional[str]]:
        """
        读取硬件错误状态 (使用逆向发现的地址66)

        Args:
            servo_id: 舵机ID

        Returns:
            (error_status, result, error)
        """
        try:
            data, result, error = self.connection.read_memory(servo_id, MemoryMap.HARDWARE_ERROR_STATUS, 1)
            if result == 0 and data and len(data) > 0:
                error_status = DataParser.bytes_to_int(data)
                return error_status, result, error
            return None, result, error

        except Exception as e:
            self.logger.error(f"读取硬件错误状态失败 ID:{servo_id}, 错误: {e}")
            return None, -1, str(e)

    def get_complete_status(self, servo_id: int) -> Dict[str, Any]:
        """
        获取舵机完整状态 (包含逆向发现的高级功能)

        Args:
            servo_id: 舵机ID

        Returns:
            完整状态字典
        """
        status = {
            'id': servo_id,
            'timestamp': time.time(),
            'basic': {},
            'advanced': {},
            'errors': []
        }

        try:
            # 基础状态 (通过SDK方法)
            if hasattr(self.connection.protocol_handler, 'ReadPos'):
                position, result, error = self.connection.protocol_handler.ReadPos(servo_id)
                if result == 0:
                    status['basic']['position'] = position

            if hasattr(self.connection.protocol_handler, 'ReadSpeed'):
                speed, result, error = self.connection.protocol_handler.ReadSpeed(servo_id)
                if result == 0:
                    status['basic']['speed'] = speed

            # 高级状态 (通过逆向发现的地址)
            # 温度
            temperature, result, error = self.read_temperature(servo_id)
            if result == 0:
                status['advanced']['temperature'] = temperature

            # 温度上限
            temp_limit, result, error = self.read_temperature_limit(servo_id)
            if result == 0:
                status['advanced']['temperature_limit'] = temp_limit
                if temperature:
                    usage_ratio = temperature / temp_limit if temp_limit > 0 else 0
                    status['advanced']['temperature_usage'] = usage_ratio

                    # 温度警告级别
                    if usage_ratio >= 0.9:
                        status['advanced']['temp_warning_level'] = 'critical'
                    elif usage_ratio >= 0.8:
                        status['advanced']['temp_warning_level'] = 'warning'
                    elif usage_ratio >= 0.6:
                        status['advanced']['temp_warning_level'] = 'caution'
                    else:
                        status['advanced']['temp_warning_level'] = 'normal'

            # 电压
            voltage, result, error = self.read_voltage(servo_id)
            if result == 0:
                status['advanced']['voltage'] = voltage

            # 电流
            current, result, error = self.read_current(servo_id)
            if result == 0:
                status['advanced']['current'] = current

            # 硬件错误状态
            hw_error, result, error = self.read_hardware_error_status(servo_id)
            if result == 0:
                status['advanced']['hardware_error'] = hw_error
                status['errors'] = self._parse_hardware_errors(hw_error)

            # 同步状态 (逆向发现)
            sync_data, result, error = self.connection.read_memory(servo_id, MemoryMap.SYNC_WRITE_FLAG, 1)
            if result == 0 and sync_data:
                status['advanced']['sync_status'] = bool(sync_data[0])

        except Exception as e:
            self.logger.error(f"获取完整状态失败 ID:{servo_id}, 错误: {e}")
            status['error'] = str(e)

        return status

    def monitor_temperature(self, duration: float, interval: float = 1.0) -> Dict[int, List[Dict[str, Any]]]:
        """
        温度监控

        Args:
            duration: 监控时长(秒)
            interval: 采样间隔(秒)

        Returns:
            温度数据字典
        """
        temp_data = {}

        try:
            # 扫描舵机
            servos = self.connection.scan_servos()
            if not servos:
                self.logger.warning("未发现舵机")
                return temp_data

            # 初始化数据结构
            for servo in servos:
                temp_data[servo['id']] = []

            start_time = time.time()
            self.logger.info(f"开始温度监控，时长: {duration}秒, 间隔: {interval}秒")

            while time.time() - start_time < duration:
                timestamp = time.time()

                for servo in servos:
                    servo_id = servo['id']

                    # 读取温度和温度上限
                    temperature, temp_result, temp_error = self.read_temperature(servo_id)
                    temp_limit, limit_result, limit_error = self.read_temperature_limit(servo_id)

                    reading = {
                        'timestamp': timestamp,
                        'temperature': temperature if temp_result == 0 else None,
                        'temperature_limit': temp_limit if limit_result == 0 else None,
                        'error': temp_error if temp_result != 0 else (limit_error if limit_result != 0 else None)
                    }

                    temp_data[servo_id].append(reading)

                    # 检查警告
                    if temperature and temp_limit:
                        usage_ratio = temperature / temp_limit
                        if usage_ratio >= 0.9:
                            self.logger.warning(f"舵机 {servo_id} 温度过高: {temperature}°C (上限: {temp_limit}°C)")

                time.sleep(interval)

            self.logger.info("温度监控完成")

        except Exception as e:
            self.logger.error(f"温度监控失败: {e}")

        return temp_data

    def start_continuous_monitoring(self, servo_ids: List[int], interval: float = 1.0,
                                  callback: Optional[Callable] = None):
        """
        开始连续监控

        Args:
            servo_ids: 要监控的舵机ID列表
            interval: 监控间隔
            callback: 状态更新回调函数
        """
        if self.is_monitoring:
            self.logger.warning("监控已在运行中")
            return

        self.is_monitoring = True
        if callback:
            self.monitor_callbacks.append(callback)

        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(servo_ids, interval),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("开始连续监控")

    def stop_continuous_monitoring(self):
        """停止连续监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        self.logger.info("停止连续监控")

    def _monitoring_loop(self, servo_ids: List[int], interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                for servo_id in servo_ids:
                    status = self.get_complete_status(servo_id)

                    # 调用回调函数
                    for callback in self.monitor_callbacks:
                        try:
                            callback(servo_id, status)
                        except Exception as e:
                            self.logger.error(f"回调函数执行失败: {e}")

                time.sleep(interval)

            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(interval)

    def add_monitor_callback(self, callback: Callable):
        """添加监控回调函数"""
        self.monitor_callbacks.append(callback)

    def _parse_hardware_errors(self, error_status: int) -> List[str]:
        """解析硬件错误状态"""
        errors = []

        if error_status & 0x01:  # ERRBIT_VOLTAGE
            errors.append("输入电压错误")
        if error_status & 0x02:  # ERRBIT_ANGLE
            errors.append("角度传感器错误")
        if error_status & 0x04:  # ERRBIT_OVERHEAT
            errors.append("过热错误")
        if error_status & 0x08:  # ERRBIT_OVERLOAD
            errors.append("过载错误")
        if error_status & 0x10:  # ERRBIT_OVERELE
            errors.append("电子错误")
        if error_status & 0x20:  # 自定义过流错误
            errors.append("过流错误")

        return errors

    def get_system_health_report(self) -> Dict[str, Any]:
        """获取系统健康报告"""
        report = {
            'timestamp': time.time(),
            'total_servos': 0,
            'healthy_servos': 0,
            'warning_servos': 0,
            'critical_servos': 0,
            'servo_details': [],
            'system_errors': []
        }

        try:
            # 扫描舵机
            servos = self.connection.scan_servos()
            report['total_servos'] = len(servos)

            for servo in servos:
                servo_id = servo['id']
                status = self.get_complete_status(servo_id)

                servo_detail = {
                    'id': servo_id,
                    'model_number': servo.get('model_number'),
                    'health_status': 'unknown',
                    'issues': []
                }

                # 健康状态评估
                temp_warning = status['advanced'].get('temp_warning_level', 'normal')
                errors = status.get('errors', [])

                if temp_warning == 'critical' or errors:
                    servo_detail['health_status'] = 'critical'
                    report['critical_servos'] += 1
                elif temp_warning == 'warning':
                    servo_detail['health_status'] = 'warning'
                    report['warning_servos'] += 1
                else:
                    servo_detail['health_status'] = 'healthy'
                    report['healthy_servos'] += 1

                if errors:
                    servo_detail['issues'].extend(errors)

                if temp_warning != 'normal':
                    temp = status['advanced'].get('temperature')
                    temp_limit = status['advanced'].get('temperature_limit')
                    if temp and temp_limit:
                        servo_detail['issues'].append(f"温度警告: {temp}°C (上限: {temp_limit}°C)")

                report['servo_details'].append(servo_detail)

        except Exception as e:
            self.logger.error(f"生成健康报告失败: {e}")
            report['system_errors'].append(str(e))

        return report