#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Logger Utility
日志工具模块
"""

import logging
import os
from datetime import datetime
from typing import Optional


class FTServoLogger:
    """FTServo日志管理器"""

    def __init__(self, name: str = 'FTServo', log_file: Optional[str] = None, level: int = logging.INFO):
        """
        初始化日志器

        Args:
            name: 日志器名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers(log_file, level)

    def _setup_handlers(self, log_file: Optional[str], level: int):
        """设置日志处理器"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs):
        """调试信息"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """一般信息"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """警告信息"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """错误信息"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """严重错误信息"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """异常信息（包含堆栈跟踪）"""
        self.logger.exception(message, *args, **kwargs)


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger: FTServoLogger):
        self.logger = logger
        self.start_time = None

    def start(self, operation: str):
        """开始计时"""
        self.start_time = datetime.now()
        self.operation = operation
        self.logger.debug(f"开始执行: {operation}")

    def end(self, operation: Optional[str] = None):
        """结束计时并记录"""
        if self.start_time is None:
            return

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() * 1000  # ms

        op_name = operation or self.operation or "未知操作"
        self.logger.info(f"执行完成: {op_name}, 耗时: {duration:.2f}ms")

        self.start_time = None
        return duration


def get_logger(name: str = 'FTServo') -> FTServoLogger:
    """获取日志器实例"""
    return FTServoLogger(name)


def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO):
    """设置全局日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file or 'ftservo.log', encoding='utf-8') if log_file else logging.NullHandler()
        ]
    )