#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Connection Manager
连接管理器 - 负责串口连接和基础通信
"""

import time
import threading
from typing import Optional, List, Tuple, Dict, Any
from ..config.settings import CommunicationConfig, ErrorCodes
from ..utils.logger import get_logger


class ConnectionManager:
    """FTServo连接管理器"""

    def __init__(self, port_name: Optional[str] = None, baud_rate: Optional[int] = None):
        """
        初始化连接管理器

        Args:
            port_name: 串口名称
            baud_rate: 波特率
        """
        self.port_name = port_name or CommunicationConfig.DEFAULT_PORT
        self.baud_rate = baud_rate or CommunicationConfig.DEFAULT_BAUDRATE
        self.logger = get_logger(f"{__name__}.ConnectionManager")

        # 连接状态
        self.is_connected = False
        self.port_handler = None
        self.protocol_handler = None
        self.connection_lock = threading.Lock()

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 0.1

    def connect(self, protocol: str = 'hls') -> bool:
        """
        连接到舵机

        Args:
            protocol: 协议类型 ('hls', 'scscl', 'sms_sts')

        Returns:
            连接是否成功
        """
        with self.connection_lock:
            if self.is_connected:
                self.logger.warning("已经连接到串口")
                return True

            try:
                # 导入SDK
                from scservo_sdk import PortHandler
                from ..config.settings import CommunicationConfig

                # 创建端口处理器
                self.port_handler = PortHandler(self.port_name)

                # 打开端口
                if not self.port_handler.openPort():
                    self.logger.error(f"无法打开串口: {self.port_name}")
                    return False

                # 设置波特率
                if not self.port_handler.setBaudRate(self.baud_rate):
                    self.logger.error(f"无法设置波特率: {self.baud_rate}")
                    self.port_handler.closePort()
                    return False

                # 创建协议处理器
                if protocol not in CommunicationConfig.PROTOCOLS:
                    self.logger.error(f"不支持的协议类型: {protocol}")
                    self.port_handler.closePort()
                    return False

                protocol_class = CommunicationConfig.PROTOCOLS[protocol]
                self.protocol_handler = protocol_class(self.port_handler)

                self.is_connected = True
                self.logger.info(f"成功连接到 {self.port_name} (波特率: {self.baud_rate}, 协议: {protocol})")
                return True

            except Exception as e:
                self.logger.error(f"连接失败: {e}")
                self._cleanup()
                return False

    def disconnect(self):
        """断开连接"""
        with self.connection_lock:
            if self.is_connected:
                self.logger.info("正在断开连接...")
                self._cleanup()
                self.is_connected = False
                self.logger.info("连接已断开")

    def _cleanup(self):
        """清理资源"""
        try:
            if self.port_handler:
                self.port_handler.closePort()
        except:
            pass

        self.port_handler = None
        self.protocol_handler = None

    def ping(self, servo_id: int) -> Tuple[Optional[int], int, Optional[int]]:
        """
        检测舵机是否存在

        Args:
            servo_id: 舵机ID

        Returns:
            (model_number, result, error)
        """
        if not self.is_connected or not self.protocol_handler:
            return None, ErrorCodes.ERROR_OPERATION_FAILED, "未连接"

        try:
            model_number, result, error = self.protocol_handler.ping(servo_id)
            return model_number, result, error
        except Exception as e:
            self.logger.error(f"ping失败 ID:{servo_id}, 错误: {e}")
            return None, ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def read_memory(self, servo_id: int, address: int, length: int) -> Tuple[Optional[bytes], int, Optional[str]]:
        """
        读取内存数据

        Args:
            servo_id: 舵机ID
            address: 内存地址
            length: 数据长度

        Returns:
            (data, result, error)
        """
        if not self.is_connected or not self.protocol_handler:
            return None, ErrorCodes.ERROR_OPERATION_FAILED, "未连接"

        try:
            data, result, error = self.protocol_handler.readTxRx(servo_id, address, length)
            return data, result, error
        except Exception as e:
            self.logger.error(f"读取内存失败 ID:{servo_id}, 地址:0x{address:02X}, 错误: {e}")
            return None, ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def write_memory(self, servo_id: int, address: int, length: int, data: bytes) -> Tuple[int, Optional[str]]:
        """
        写入内存数据

        Args:
            servo_id: 舵机ID
            address: 内存地址
            length: 数据长度
            data: 写入数据

        Returns:
            (result, error)
        """
        if not self.is_connected or not self.protocol_handler:
            return ErrorCodes.ERROR_OPERATION_FAILED, "未连接"

        try:
            result, error = self.protocol_handler.writeTxRx(servo_id, address, length, data)
            return result, error
        except Exception as e:
            self.logger.error(f"写入内存失败 ID:{servo_id}, 地址:0x{address:02X}, 错误: {e}")
            return ErrorCodes.ERROR_OPERATION_FAILED, str(e)

    def scan_servos(self, start_id: int = 1, end_id: int = 20) -> List[Dict[str, Any]]:
        """
        扫描舵机

        Args:
            start_id: 起始ID
            end_id: 结束ID

        Returns:
            发现的舵机列表
        """
        if not self.is_connected:
            self.logger.error("未连接到串口")
            return []

        servos = []
        self.logger.info(f"开始扫描舵机 (ID: {start_id}-{end_id})")

        for servo_id in range(start_id, end_id + 1):
            self.logger.debug(f"检测舵机 ID: {servo_id}")

            model_number, result, error = self.ping(servo_id)

            if result == ErrorCodes.COMM_SUCCESS:
                servo_info = {
                    'id': servo_id,
                    'model_number': model_number,
                    'connected': True
                }
                servos.append(servo_info)
                self.logger.info(f"发现舵机 ID: {servo_id}, 型号: {model_number}")

        self.logger.info(f"扫描完成，发现 {len(servos)} 个舵机")
        return servos

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态信息"""
        return {
            'is_connected': self.is_connected,
            'port_name': self.port_name,
            'baud_rate': self.baud_rate,
            'protocol': type(self.protocol_handler).__name__ if self.protocol_handler else None
        }

    def reset_connection(self) -> bool:
        """重置连接"""
        self.logger.info("重置连接...")
        self.disconnect()
        time.sleep(0.5)
        return self.connect()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()