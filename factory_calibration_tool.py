#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EZ Tool - 简化版双串口工厂舵机标定工具
基于原始工具，只增加一个中间值校准按钮
"""

import sys
import time
import threading
import subprocess
import os
from typing import List
from queue import Queue

# 添加必要的路径
sys.path.append('.')
sys.path.append('./scservo_sdk')

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGridLayout, QGroupBox,
    QMessageBox, QFrame, QStatusBar, QSplitter, QComboBox
)
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtGui import QFont, QPalette, QColor

from scservo_sdk.port_handler import PortHandler
from scservo_sdk.sms_sts import sms_sts
from scservo_sdk.scservo_def import COMM_SUCCESS


class RemoteControlWorker(QObject):
    """遥控操作后台工作线程"""
    status_updated = Signal(str)  # 状态更新信号
    log_message = Signal(str)   # 日志消息信号
    control_started = Signal()  # 遥控启动信号
    control_stopped = Signal()  # 遥控停止信号

    def __init__(self, read_port=None, control_port=None):
        super().__init__()
        self.remote_process = None
        self.running = False
        self.project_root = os.path.abspath(os.path.dirname(__file__))
        self.read_port = read_port
        self.control_port = control_port

    def start_remote_control(self):
        """启动遥控操作"""
        if self.running:
            return False, "遥控操作已在运行"

        try:
            # 构建超快遥控脚本的路径
            remote_script_path = os.path.join(os.path.dirname(__file__), 'servo_remote_control.py')

            if not os.path.exists(remote_script_path):
                return False, f"遥控脚本不存在: {remote_script_path}"

            # 构建命令参数
            command = [sys.executable, remote_script_path]
            if self.read_port:
                command.extend(['--read-port', self.read_port])
            if self.control_port:
                command.extend(['--control-port', self.control_port])

            # 启动子进程运行遥控脚本
            self.remote_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=self.project_root
            )

            self.running = True
            self.log_message.emit("🚀 遥控操作已启动 (10ms更新间隔)")
            self.control_started.emit()

            # 启动监控线程
            threading.Thread(target=self._monitor_process, daemon=True).start()

            return True, "遥控操作启动成功"

        except Exception as e:
            return False, f"启动遥控操作失败: {e}"

    def stop_remote_control(self):
        """停止遥控操作"""
        if not self.running:
            return False, "遥控操作未运行"

        try:
            if self.remote_process:
                self.remote_process.terminate()
                # 等待进程正常退出
                try:
                    self.remote_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果5秒内没有退出，强制杀死
                    self.remote_process.kill()
                    self.remote_process.wait()

            self.running = False
            self.remote_process = None
            self.log_message.emit("⏹️ 遥控操作已停止")
            self.control_stopped.emit()
            return True, "遥控操作停止成功"

        except Exception as e:
            return False, f"停止遥控操作失败: {e}"

    def _monitor_process(self):
        """监控遥控进程的输出"""
        if not self.remote_process:
            return

        try:
            while self.running and self.remote_process.poll() is None:
                line = self.remote_process.stdout.readline()
                if line:
                    line = line.strip()
                    if line:
                        self.log_message.emit(f"遥控: {line}")
                time.sleep(0.1)

            # 进程结束
            if self.remote_process.poll() is not None:
                self.running = False
                self.remote_process = None
                self.log_message.emit("🔚 遥控进程已结束")
                self.control_stopped.emit()

        except Exception as e:
            self.log_message.emit(f"监控遥控进程异常: {e}")
            self.running = False
            self.control_stopped.emit()


class ServoWorker(QObject):
    """单个舵机控制工作线程"""
    status_updated = Signal(list, bool, str)  # 舵机列表, 连接状态, 端口标识
    id_changed = Signal(int, int, bool, str, str)  # old_id, new_id, success, message, 端口标识
    log_message = Signal(str, str)  # 日志消息, 端口标识

    def __init__(self, port_name: str, port_id: str):
        super().__init__()
        self.port_name = port_name
        self.port_id = port_id  # 端口标识 (left/right)
        self.port_handler = None
        self.servo_handler = None
        self.is_connected = False
        self.current_servos = []
        self.running = False

        # 连接配置
        self.baud_rate = 1000000

        # ID修改队列
        self.id_change_queue = Queue()
        self.id_change_thread = None
        self.id_change_running = False

        # 扫描控制
        self.pause_scanning = False  # 是否暂停扫描

    def connect_servo(self) -> bool:
        """连接舵机控制器"""
        try:
            print(f"[DEBUG] {self.port_id}: Attempting to connect to {self.port_name}")
            self.log_message.emit(f"正在连接舵机控制器: {self.port_name}", self.port_id)
            self.port_handler = PortHandler(self.port_name)

            if not self.port_handler.openPort():
                print(f"[DEBUG] {self.port_id}: Failed to open port {self.port_name}")
                self.log_message.emit(f"❌ 无法打开串口: {self.port_name}", self.port_id)
                return False

            if not self.port_handler.setBaudRate(self.baud_rate):
                print(f"[DEBUG] {self.port_id}: Failed to set baud rate {self.baud_rate}")
                self.log_message.emit(f"❌ 无法设置波特率: {self.baud_rate}", self.port_id)
                self.port_handler.closePort()
                return False

            self.servo_handler = sms_sts(self.port_handler)
            self.is_connected = True
            print(f"[DEBUG] {self.port_id}: Successfully connected to {self.port_name}")
            self.log_message.emit("✅ 舵机控制器连接成功", self.port_id)
            return True

        except Exception as e:
            print(f"[DEBUG] {self.port_id}: Connection exception: {e}")
            self.log_message.emit(f"❌ 连接失败: {e}", self.port_id)
            return False

    def disconnect_servo(self):
        """断开舵机连接"""
        try:
            if self.port_handler:
                self.port_handler.closePort()
                self.is_connected = False
                self.log_message.emit("🔌 舵机控制器已断开", self.port_id)
        except:
            pass

    def ping_servo(self, servo_id: int) -> bool:
        """检测舵机是否存在"""
        try:
            model_number, result, error = self.servo_handler.ping(servo_id)
            if result == COMM_SUCCESS:
                print(f"[DEBUG] {self.port_id}: 舵机 {servo_id} 型号: {model_number}")
                return True
            else:
                print(f"[DEBUG] {self.port_id}: Ping 舵机 {servo_id} 失败: result={result}, error={error}")
                return False
        except Exception as e:
            print(f"[DEBUG] {self.port_id}: Ping 舵机 {servo_id} 异常: {e}")
            return False

    def scan_servos(self) -> List[int]:
        """扫描所有舵机"""
        if not self.is_connected:
            return []

        found_servos = []
        for servo_id in range(1, 10):  # 扫描所有可能的ID
            if self.ping_servo(servo_id):
                found_servos.append(servo_id)

        return found_servos

    def change_servo_id(self, old_id: int, new_id: int) -> (bool, str):
        """修改舵机ID（队列版本）"""
        # 将请求加入队列
        self.queue_id_change(old_id, new_id)
        return True, "ID修改请求已加入队列"

    def queue_id_change(self, old_id: int, new_id: int):
        """将ID修改请求加入队列"""
        print(f"[DEBUG] {self.port_id}: ID修改请求入队: {old_id} -> {new_id}")
        self.log_message.emit(f"📝 ID修改请求已排队: {old_id} -> {new_id}", self.port_id)
        self.id_change_queue.put((old_id, new_id, time.time()))

        # 启动ID修改线程（如果还没启动）
        if not self.id_change_running:
            self.start_id_change_processor()

    def start_id_change_processor(self):
        """启动ID修改处理线程"""
        if not self.id_change_running:
            self.id_change_running = True
            self.id_change_thread = threading.Thread(target=self.process_id_changes, daemon=True)
            self.id_change_thread.start()
            print(f"[DEBUG] {self.port_id}: ID修改处理线程已启动")

    def process_id_changes(self):
        """处理ID修改队列"""
        print(f"[DEBUG] {self.port_id}: 开始处理ID修改队列")
        while self.id_change_running or not self.id_change_queue.empty():
            try:
                if not self.id_change_queue.empty():
                    old_id, new_id, request_time = self.id_change_queue.get(timeout=1)

                    # 暂停扫描，避免总线冲突
                    self.pause_scanning = True
                    print(f"[DEBUG] {self.port_id}: 暂停扫描，准备执行ID修改: {old_id} -> {new_id}")
                    self.log_message.emit(f"⏸️ 暂停扫描，执行ID修改: {old_id} -> {new_id}", self.port_id)

                    # 等待一下确保扫描完全停止
                    time.sleep(0.5)

                    # 执行ID修改
                    success, message = self.execute_id_change(old_id, new_id)

                    # 恢复扫描
                    self.pause_scanning = False
                    print(f"[DEBUG] {self.port_id}: 恢复扫描")
                    self.log_message.emit(f"▶️ 恢复扫描", self.port_id)

                    # 发送结果
                    self.id_changed.emit(old_id, new_id, success, message, self.port_id)

                else:
                    time.sleep(0.1)  # 短暂休眠避免CPU占用

            except Exception as e:
                print(f"[DEBUG] {self.port_id}: ID修改处理异常: {e}")
                self.log_message.emit(f"❌ ID修改处理异常: {e}", self.port_id)
                # 确保扫描被恢复
                self.pause_scanning = False

        print(f"[DEBUG] {self.port_id}: ID修改处理线程结束")
        self.id_change_running = False
        self.pause_scanning = False

    def execute_id_change(self, old_id: int, new_id: int) -> (bool, str):
        """执行实际的ID修改操作"""
        try:
            if not self.is_connected:
                return False, "未连接舵机控制器"

            self.log_message.emit(f"🔧 执行SMS_STS ID修改: {old_id} -> {new_id}", self.port_id)
            print(f"[DEBUG] {self.port_id}: 执行ID修改: {old_id} -> {new_id}")

            # 首先读取舵机信息（此时扫描已暂停，不会冲突）
            try:
                model_number, result, error = self.servo_handler.ping(old_id)
                if result == COMM_SUCCESS:
                    print(f"[DEBUG] {self.port_id}: SMS_STS 舵机型号: {model_number}")
                    self.log_message.emit(f"📋 舵机型号: {model_number}", self.port_id)
                else:
                    print(f"[DEBUG] {self.port_id}: 无法读取舵机信息: {error}")
                    return False, f"无法读取舵机信息: {error}"
            except Exception as e:
                return False, f"读取舵机信息异常: {e}"

            # SMS_STS EEPROM解锁流程
            print(f"[DEBUG] {self.port_id}: SMS_STS 解锁EEPROM...")
            result, error = self.servo_handler.unLockEprom(old_id)
            if result != COMM_SUCCESS:
                print(f"[DEBUG] {self.port_id}: EEPROM解锁失败: result={result}, error={error}")
                return False, f"EEPROM解锁失败: {error}"

            print(f"[DEBUG] {self.port_id}: EEPROM解锁成功")
            time.sleep(0.1)

            # 修改ID (使用SMS_STS_ID地址)
            print(f"[DEBUG] {self.port_id}: 写入新ID: {new_id}")
            result, error = self.servo_handler.write1ByteTxRx(old_id, 5, new_id)  # SMS_STS_ID = 5
            if result != COMM_SUCCESS:
                print(f"[DEBUG] {self.port_id}: ID写入失败: result={result}, error={error}")
                return False, f"ID写入失败: {error}"

            print(f"[DEBUG] {self.port_id}: ID写入成功")
            time.sleep(0.3)

            # 验证新ID（此时扫描仍暂停，ping不会冲突）
            print(f"[DEBUG] {self.port_id}: 验证新ID: {new_id}")
            if not self.ping_servo(new_id):
                print(f"[DEBUG] {self.port_id}: 新ID验证失败")
                return False, f"验证失败，无法ping通新ID: {new_id}"

            print(f"[DEBUG] {self.port_id}: 新ID验证成功")

            # 重新锁定EEPROM
            print(f"[DEBUG] {self.port_id}: 重新锁定EEPROM...")
            result, error = self.servo_handler.LockEprom(new_id)
            if result != COMM_SUCCESS:
                print(f"[DEBUG] {self.port_id}: 重新锁定失败: {error}")
                self.log_message.emit(f"⚠️ 重新锁定EEPROM失败: {error}", self.port_id)
            else:
                print(f"[DEBUG] {self.port_id}: 重新锁定成功")

            self.log_message.emit(f"✅ SMS_STS ID修改成功: {old_id} -> {new_id}", self.port_id)
            print(f"[DEBUG] {self.port_id}: ID修改完成: {old_id} -> {new_id}")
            return True, ""

        except Exception as e:
            error_msg = f"修改ID异常: {e}"
            print(f"[DEBUG] {self.port_id}: 修改ID异常: {e}")
            self.log_message.emit(f"❌ {error_msg}", self.port_id)
            return False, error_msg

    def run_scanner(self):
        """运行扫描循环"""
        scan_count = 0
        self.running = True
        consecutive_failures = 0
        max_failures = 3

        self.log_message.emit("🚀 扫描线程启动", self.port_id)
        print(f"[DEBUG] {self.port_id}: Scanner thread started")

        # 首次连接
        if not self.is_connected:
            self.connect_servo()

        while self.running:
            try:
                scan_count += 1

                # 如果未连接，尝试重新连接
                if not self.is_connected:
                    if consecutive_failures < max_failures:
                        self.log_message.emit(f"🔄 尝试重新连接... (第{consecutive_failures + 1}次)", self.port_id)
                        time.sleep(2)  # 等待2秒再重试
                        if self.connect_servo():
                            consecutive_failures = 0  # 重置失败计数
                        else:
                            consecutive_failures += 1
                        continue
                    else:
                        # 失败次数过多，延长等待时间
                        self.log_message.emit(f"⚠️ 连续失败{max_failures}次，等待10秒后重试...", self.port_id)
                        time.sleep(10)
                        consecutive_failures = 0  # 重置计数
                        continue

                # 检查是否暂停扫描（ID修改期间）
                if self.pause_scanning:
                    print(f"[DEBUG] {self.port_id}: 扫描已暂停（ID修改中）")
                    time.sleep(0.5)  # 短暂休眠，减少CPU占用
                    continue

                # 扫描舵机
                new_servos = self.scan_servos()
                print(f"[DEBUG] {self.port_id}: Scan result: {new_servos}, current: {self.current_servos}")

                # 如果扫描成功，重置失败计数
                if new_servos is not None:
                    consecutive_failures = 0

                    # 如果舵机列表有变化
                    if new_servos != self.current_servos:
                        old_servos = self.current_servos.copy() if self.current_servos else []
                        self.current_servos = new_servos

                        if new_servos:
                            if not old_servos:
                                self.log_message.emit(f"📡 发现舵机: {new_servos}", self.port_id)
                            else:
                                added = set(new_servos) - set(old_servos)
                                removed = set(old_servos) - set(new_servos)
                                changes = []
                                if added:
                                    changes.append(f"新增: {list(added)}")
                                if removed:
                                    changes.append(f"移除: {list(removed)}")
                                self.log_message.emit(f"📡 舵机变化: {', '.join(changes)}", self.port_id)
                        else:
                            if old_servos:
                                self.log_message.emit("📡 所有舵机已断开", self.port_id)

                        print(f"[DEBUG] {self.port_id}: Emitting status_updated: servos={new_servos}, connected={self.is_connected}")
                        self.status_updated.emit(self.current_servos, self.is_connected, self.port_id)

                # 每30次扫描显示一次状态（减少日志频率）
                if scan_count % 30 == 0:
                    if self.current_servos:
                        self.log_message.emit(f"📊 当前舵机ID: {self.current_servos}", self.port_id)
                    else:
                        self.log_message.emit("📊 当前无舵机", self.port_id)

                time.sleep(1)  # 扫描间隔

            except Exception as e:
                consecutive_failures += 1
                self.log_message.emit(f"❌ 扫描异常: {e} (失败次数: {consecutive_failures})", self.port_id)
                # 不要立即断开连接，给下次重试机会
                time.sleep(1)

    def start(self):
        """启动工作线程"""
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_scanner, daemon=True).start()

    def stop(self):
        """停止工作线程"""
        self.running = False
        self.id_change_running = False
        self.disconnect_servo()

        # 等待ID修改线程结束
        if self.id_change_thread and self.id_change_thread.is_alive():
            self.id_change_thread.join(timeout=2)


class ServoPanel(QWidget):
    """单个舵机控制面板"""

    def __init__(self, port_name: str, port_id: str):
        super().__init__()
        self.port_name = port_name
        self.port_id = port_id
        self.worker = ServoWorker(port_name, port_id)
        self.init_ui()
        self.init_connections()
        self.worker.start()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 标题
        self.title_label = QLabel(f"🏭 {self.port_name} - 舵机标定")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px;")
        layout.addWidget(self.title_label)

        # 状态面板
        self.create_status_panel(layout)

        # 舵机状态面板
        self.create_servo_panel(layout)

        # 标定面板
        self.create_calibration_panel(layout)

        # 日志面板
        self.create_log_panel(layout)

        # 设置整体样式
        self.setStyleSheet(f"""
            QWidget#{self.port_id} {{
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 10px;
                background-color: #ffffff;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 5px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
            }}
            QPushButton {{
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0056b3;
            }}
            QPushButton:pressed {{
                background-color: #004085;
            }}
            QPushButton:disabled {{
                background-color: #6c757d;
            }}
            QTextEdit {{
                background-color: #f8f9fa;
                color: #212529;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
            QLabel {{
                color: #495057;
            }}
        """)
        self.setObjectName(self.port_id)

    def create_status_panel(self, layout):
        """创建状态面板"""
        status_group = QGroupBox("📡 系统状态")
        status_layout = QHBoxLayout()
        status_group.setLayout(status_layout)

        # 连接状态
        self.connection_status = QLabel("🔴 未连接")
        self.connection_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.connection_status)

        status_layout.addStretch()

        # 当前舵机
        self.current_servos_label = QLabel("当前舵机: 扫描中...")
        self.current_servos_label.setStyleSheet("font-size: 12px;")
        status_layout.addWidget(self.current_servos_label)

        layout.addWidget(status_group)

    def create_servo_panel(self, layout):
        """创建舵机状态面板"""
        servo_group = QGroupBox("📡 舵机状态")
        servo_layout = QVBoxLayout()
        servo_group.setLayout(servo_layout)

        # 舵机列表
        self.servo_list = QTextEdit()
        self.servo_list.setReadOnly(True)
        self.servo_list.setMaximumHeight(150)
        self.servo_list.setPlainText("正在扫描舵机...")
        servo_layout.addWidget(self.servo_list)

        layout.addWidget(servo_group)

    def create_calibration_panel(self, layout):
        """创建标定面板"""
        calibration_group = QGroupBox("🎯 ID标定")
        calibration_layout = QVBoxLayout()
        calibration_group.setLayout(calibration_layout)

        # 说明文字
        info_label = QLabel("📋 点击目标ID执行修改\n⏸️ 自动暂停扫描确保成功")
        info_label.setStyleSheet("background-color: #e3f2fd; border: 1px solid #bbdefb; padding: 8px; border-radius: 4px; color: #1565c0; font-size: 11px;")
        calibration_layout.addWidget(info_label)

        # ID按钮网格
        self.id_buttons = []
        button_layout = QGridLayout()

        for i in range(6):
            row = i // 3
            col = i % 3

            btn = QPushButton(str(i + 1))
            btn.setMinimumHeight(60)
            btn.setMinimumWidth(80)
            btn.setStyleSheet("font-size: 24px;")
            btn.clicked.connect(lambda checked, id_val=i+1: self.change_servo_id(id_val))
            btn.setEnabled(False)

            self.id_buttons.append(btn)
            button_layout.addWidget(btn, row, col)

        calibration_layout.addLayout(button_layout)
        layout.addWidget(calibration_group)

    def create_log_panel(self, layout):
        """创建日志面板"""
        log_group = QGroupBox("📋 操作日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setPlainText("系统启动...")
        log_layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.setMaximumWidth(80)
        clear_btn.setStyleSheet("font-size: 11px;")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group)

    def init_connections(self):
        """初始化信号连接"""
        self.worker.status_updated.connect(self.update_status)
        self.worker.id_changed.connect(self.on_id_changed)
        self.worker.log_message.connect(self.add_log)

        # 添加初始连接日志
        self.add_log("🔄 信号连接已建立", self.port_id)
        self.add_log("📡 开始扫描舵机...", self.port_id)

    def update_status(self, servos, connected, port_id):
        """更新状态显示"""
        if port_id != self.port_id:
            return

        print(f"[DEBUG] {port_id} update_status called: servos={servos}, connected={connected}")
        if connected:
            self.connection_status.setText("🟢 已连接")
            self.connection_status.setStyleSheet("color: #28a745; font-size: 12px; font-weight: bold;")
        else:
            self.connection_status.setText("🔴 未连接")
            self.connection_status.setStyleSheet("color: #dc3545; font-size: 12px; font-weight: bold;")

        if servos:
            self.current_servos_label.setText(f"当前舵机: {', '.join(map(str, servos))}")
            self.servo_list.setPlainText("📡 发现的舵机：\n\n" + "\n".join([f"• 舵机 ID: {servo_id}" for servo_id in servos]))
        else:
            self.current_servos_label.setText("当前舵机: 无")
            self.servo_list.setPlainText("📡 未发现舵机\n\n请检查:\n1. 舵机控制器是否连接\n2. 舵机是否通电\n3. 串口配置是否正确")

        # 更新按钮状态
        self.update_button_states(servos, connected)

    def update_button_states(self, servos, connected):
        """更新按钮状态"""
        has_servos = connected and len(servos) > 0

        for i, btn in enumerate(self.id_buttons):
            target_id = i + 1
            is_assigned = target_id in servos

            btn.setEnabled(has_servos and not is_assigned)

            if is_assigned:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #6c757d;
                        color: white;
                        font-size: 24px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        font-size: 24px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)

    def change_servo_id(self, target_id):
        """修改舵机ID"""
        if not self.worker.current_servos:
            QMessageBox.warning(self, "警告", "没有可用的舵机进行ID修改")
            return

        # 优先使用第一个可用的舵机
        old_id = self.worker.current_servos[0]

        # 确认对话框
        reply = QMessageBox.question(
            self,
            f"确认修改ID ({self.port_name})",
            f"确定要将舵机 ID {old_id} 修改为 ID {target_id} 吗？\n\n系统将自动暂停扫描确保修改成功。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.add_log(f"🎯 提交ID修改请求: {old_id} -> {target_id}", self.port_id)

            # 将请求加入队列（立即返回）
            success, message = self.worker.change_servo_id(old_id, target_id)

            if success:
                self.add_log(f"✅ {message}", self.port_id)
                # 禁用按钮，防止重复提交
                for btn in self.id_buttons:
                    if btn.text() == str(target_id):
                        btn.setEnabled(False)
                        btn.setStyleSheet("background-color: #ffc107; color: black; font-size: 24px;")
                        break
            else:
                self.add_log(f"❌ {message}", self.port_id)

    def on_id_changed(self, old_id, new_id, success, message, port_id):
        """处理ID修改结果"""
        if port_id != self.port_id:
            return

        print(f"[DEBUG] {port_id} on_id_changed called: {old_id} -> {new_id}, success={success}, message={message}")

        # 恢复按钮状态
        for btn in self.id_buttons:
            if btn.text() == str(new_id):
                btn.setEnabled(True)
                break

        if success:
            QMessageBox.information(self, f"修改成功 ({self.port_name})", f"ID修改成功！\n{old_id} -> {new_id}")
            # 强制重新扫描舵机列表
            self.add_log(f"🔄 ID修改成功，重新扫描舵机...", self.port_id)
            # 给舵机一点时间响应新ID
            time.sleep(0.5)
            # 更新内部的舵机列表
            if old_id in self.worker.current_servos:
                self.worker.current_servos.remove(old_id)
            if new_id not in self.worker.current_servos:
                self.worker.current_servos.append(new_id)
            self.worker.current_servos.sort()
            # 手动触发状态更新
            self.update_status(self.worker.current_servos, self.worker.is_connected, self.port_id)
        else:
            QMessageBox.critical(self, f"修改失败 ({self.port_name})", f"ID修改失败！\n{message}")
            self.add_log(f"❌ 队列中ID修改失败: {old_id} -> {new_id}", self.port_id)

    def add_log(self, message, port_id):
        """添加日志消息"""
        if port_id != self.port_id:
            return

        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        # Remove emojis for console output
        clean_message = message.encode('ascii', 'ignore').decode('ascii')
        clean_log_entry = f"[{timestamp}] {clean_message}"
        print(f"[DEBUG {port_id}] {clean_log_entry}")
        self.log_text.append(log_entry)

        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 限制日志行数 - 修复Qt API错误
        document = self.log_text.document()
        if document.blockCount() > 500:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()

    def update_port_name(self, new_port_name: str):
        """更新端口名称和标题"""
        self.port_name = new_port_name
        self.title_label.setText(f"🏭 {self.port_name} - 舵机标定")

    def stop(self):
        """停止工作线程"""
        self.worker.stop()


class EZToolUI(QMainWindow):
    """EZ Tool - 简化版双串口工厂舵机标定工具"""

    def __init__(self, left_port: str = "COM1", right_port: str = "COM2"):
        super().__init__()
        self.left_port = left_port
        self.right_port = right_port

        # 遥控工作线程
        self.remote_worker = None

        # 可用串口列表
        self.available_ports = []

        self.init_ui()
        self.init_connections()
        self.refresh_ports()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("🏭 双串口工厂舵机标定工具")
        self.setGeometry(50, 50, 1600, 900)

        # 设置字体
        font = QFont("Microsoft YaHei", 10)
        self.setFont(font)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)

        # 创建顶部标题栏（包含串口选择、遥控按钮和中间值校准按钮）
        header_layout = QHBoxLayout()

        # 左侧标题
        title_label = QLabel("🏭 双串口工厂舵机标定工具")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)

        # 串口选择区域
        port_selection_group = QGroupBox("串口选择")
        port_selection_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 5px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
                color: #495057;
            }
        """)
        port_selection_layout = QHBoxLayout(port_selection_group)
        port_selection_layout.setSpacing(10)

        # 左串口选择
        left_port_layout = QVBoxLayout()
        left_port_layout.setSpacing(2)
        left_label = QLabel("串口1:")
        left_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        left_port_layout.addWidget(left_label)

        self.left_port_combo = QComboBox()
        self.left_port_combo.setMinimumWidth(80)
        self.left_port_combo.setMaximumWidth(120)
        self.left_port_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 3px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border: 1px solid #80bdff;
            }
        """)
        self.left_port_combo.currentTextChanged.connect(self.on_left_port_changed)
        left_port_layout.addWidget(self.left_port_combo)
        port_selection_layout.addLayout(left_port_layout)

        # 右串口选择
        right_port_layout = QVBoxLayout()
        right_port_layout.setSpacing(2)
        right_label = QLabel("串口2:")
        right_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        right_port_layout.addWidget(right_label)

        self.right_port_combo = QComboBox()
        self.right_port_combo.setMinimumWidth(80)
        self.right_port_combo.setMaximumWidth(120)
        self.right_port_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 3px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border: 1px solid #80bdff;
            }
        """)
        self.right_port_combo.currentTextChanged.connect(self.on_right_port_changed)
        right_port_layout.addWidget(self.right_port_combo)
        port_selection_layout.addLayout(right_port_layout)

        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #138496, stop:1 #117a8b);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #117a8b, stop:1 #0c5460);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_ports)
        refresh_btn.setToolTip("刷新串口列表")
        port_selection_layout.addWidget(refresh_btn)

        header_layout.addWidget(port_selection_group)

        # 添加6个按钮水平排列区域
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # 创建水平排列的6个按钮容器
        buttons_container = QWidget()
        buttons_container_layout = QVBoxLayout(buttons_container)
        buttons_container_layout.setSpacing(3)
        buttons_container_layout.setContentsMargins(0, 0, 0, 0)

        # 按钮行布局 - 6个按钮水平排开
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        # 串口1中位校准按钮
        self.left_calib_btn = QPushButton("串口1中位校准")
        self.left_calib_btn.setFixedSize(100, 35)
        self.left_calib_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4caf50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #035b69);
            }
        """)
        self.left_calib_btn.clicked.connect(self.run_quick_calibration_left)
        buttons_row.addWidget(self.left_calib_btn)

        # 串口1中位测试按钮
        self.left_test_btn = QPushButton("串口1中位测试")
        self.left_test_btn.setFixedSize(100, 35)
        self.left_test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196f3, stop:1 #1976d2);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976d2, stop:1 #1565c0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1565c0, stop:1 #0d47a1);
            }
        """)
        self.left_test_btn.clicked.connect(self.run_quick_test_left)
        buttons_row.addWidget(self.left_test_btn)

        # 串口1失能电机按钮
        self.left_disable_btn = QPushButton("串口1失能电机")
        self.left_disable_btn.setFixedSize(100, 35)
        self.left_disable_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff9800, stop:1 #f57c00);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f57c00, stop:1 #ef6c00);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef6c00, stop:1 #e65100);
            }
        """)
        self.left_disable_btn.clicked.connect(self.run_quick_disable_left)
        buttons_row.addWidget(self.left_disable_btn)

        # 分隔线
        separator_label = QLabel("|")
        separator_label.setStyleSheet("color: #ccc; font-size: 20px; margin: 0 5px;")
        buttons_row.addWidget(separator_label)

        # 串口2中位校准按钮
        self.right_calib_btn = QPushButton("串口2中位校准")
        self.right_calib_btn.setFixedSize(100, 35)
        self.right_calib_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4caf50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #035b69);
            }
        """)
        self.right_calib_btn.clicked.connect(self.run_quick_calibration_right)
        buttons_row.addWidget(self.right_calib_btn)

        # 串口2中位测试按钮
        self.right_test_btn = QPushButton("串口2中位测试")
        self.right_test_btn.setFixedSize(100, 35)
        self.right_test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196f3, stop:1 #1976d2);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976d2, stop:1 #1565c0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1565c0, stop:1 #0d47a1);
            }
        """)
        self.right_test_btn.clicked.connect(self.run_quick_test_right)
        buttons_row.addWidget(self.right_test_btn)

        # 串口2失能电机按钮
        self.right_disable_btn = QPushButton("串口2失能电机")
        self.right_disable_btn.setFixedSize(100, 35)
        self.right_disable_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff9800, stop:1 #f57c00);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f57c00, stop:1 #ef6c00);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef6c00, stop:1 #e65100);
            }
        """)
        self.right_disable_btn.clicked.connect(self.run_quick_disable_right)
        buttons_row.addWidget(self.right_disable_btn)

        buttons_container_layout.addLayout(buttons_row)
        buttons_layout.addWidget(buttons_container)

        header_layout.addLayout(buttons_layout)

        header_layout.addStretch()

        # 右上角遥控按钮
        self.remote_btn = QPushButton("🎮 遥控")
        self.remote_btn.setFixedSize(100, 40)
        self.remote_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #035b69);
            }
        """)
        self.remote_btn.clicked.connect(self.toggle_remote_control)
        header_layout.addWidget(self.remote_btn)

        main_layout.addLayout(header_layout)

        # 创建副标题
        # subtitle_label = QLabel("双串口工厂舵机标定工具 - 支持中位校准、测试、失能功能")
        # subtitle_label.setAlignment(Qt.AlignCenter)
        # subtitle_label.setStyleSheet("font-size: 14px; color: #6c757d; margin-bottom: 10px;")
        # main_layout.addWidget(subtitle_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 创建左侧面板
        self.left_panel = ServoPanel(self.left_port, "left")
        splitter.addWidget(self.left_panel)

        # 创建右侧面板
        self.right_panel = ServoPanel(self.right_port, "right")
        splitter.addWidget(self.right_panel)

        # 设置分割器比例
        splitter.setSizes([800, 800])

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("双串口系统已启动 - 左右独立操作 + 中间值校准")

        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
        """)

    def init_connections(self):
        """初始化信号连接"""
        # 添加初始日志
        self.status_bar.showMessage("双串口系统已启动 - 左右独立操作 + 中间值校准", 3000)

    def toggle_remote_control(self):
        """切换遥控操作"""
        if self.remote_worker is None:
            # 创建遥控工作线程，传递当前选择的端口
            self.remote_worker = RemoteControlWorker(
                read_port=self.left_port,    # 左端口用于读取
                control_port=self.right_port # 右端口用于控制
            )
            self.remote_worker.log_message.connect(self.add_remote_log)
            self.remote_worker.control_started.connect(self.on_remote_started)
            self.remote_worker.control_stopped.connect(self.on_remote_stopped)

        if not self.remote_worker.running:
            # 启动遥控操作
            self.start_remote_control()
        else:
            # 停止遥控操作
            self.stop_remote_control()

    def start_remote_control(self):
        """启动遥控操作"""
        # 停止现有的舵机标定操作，避免端口冲突
        if self.left_panel.worker.is_connected:
            self.left_panel.worker.stop()
        if self.right_panel.worker.is_connected:
            self.right_panel.worker.stop()

        # 启动遥控操作
        success, message = self.remote_worker.start_remote_control()

        if success:
            self.remote_btn.setText("⏹️ 停止")
            self.remote_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ef4444, stop:1 #dc2626);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #dc2626, stop:1 #b91c1c);
                }
            """)
            self.add_remote_log(f"✅ {message}")
            self.status_bar.showMessage("遥控操作已启动 - COM7读取，COM8控制", 5000)
        else:
            self.add_remote_log(f"❌ {message}")
            QMessageBox.critical(self, "启动失败", f"无法启动遥控操作:\n{message}")

    def stop_remote_control(self):
        """停止遥控操作"""
        if self.remote_worker is None:
            return False

        success, message = self.remote_worker.stop_remote_control()

        if success:
            self.remote_btn.setText("🎮 遥控")
            self.remote_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #10b981, stop:1 #059669);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #059669, stop:1 #047857);
                }
                """)
            self.add_remote_log(f"✅ {message}")
            self.status_bar.showMessage("遥控操作已停止", 3000)

            # 重新启动舵机标定操作
            self.left_panel.worker.start()
            self.right_panel.worker.start()
        else:
            self.add_remote_log(f"❌ {message}")

    def run_middle_calibration(self, port_name: str):
        """运行指定端口的中值校准"""
        # 直接执行指定端口的中间值校准脚本
        cali_script_path = os.path.join(os.path.dirname(__file__), 'servo_middle_calibration.py')
        command = [sys.executable, cali_script_path, port_name]

        self.add_remote_log(f"🚀 启动{port_name}中间值校准...")
        print(f"[CAL] Starting calibration for {port_name}")

        success, message = self.run_calibration_process(command)

        return success, message

    def run_calibration_process(self, command: list):
        """执行校准进程并监控输出"""
        try:
            print(f"[CALIBRATION] Command: {' '.join(command)}")

            # 启动进程
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )

            # 监控输出
            while process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            print(f"[CALIBRATION] {line}")
                    time.sleep(0.1)
                except:
                    break

            # 等待进程完成
            return_code = process.wait()

            if return_code == 0:
                return True, "校准完成"
            else:
                return False, f"校准失败，退出码: {return_code}"

        except Exception as e:
            return False, f"校准执行异常: {e}"

    def run_quick_calibration(self, port_name: str):
        """快速中位校准 - 非阻塞执行"""
        self.add_remote_log(f"🔧 开始{port_name}快速中位校准...")
        self.status_bar.showMessage(f"正在执行{port_name}中位校准...", 5000)

        # 先停止相应端口的工作线程，避免端口冲突
        if port_name == self.left_port and self.left_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备校准")
            self.left_panel.worker.stop()
        elif port_name == self.right_port and self.right_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备校准")
            self.right_panel.worker.stop()

        # 等待端口释放
        import time
        time.sleep(1.0)

        # 使用线程非阻塞执行
        from threading import Thread
        thread = Thread(target=self._execute_quick_calibration, args=(port_name,))
        thread.daemon = True
        thread.start()

        self.add_remote_log(f"📝 {port_name}校准进程已启动，请等待执行完成")

    def _execute_quick_calibration(self, port_name: str):
        """执行快速中位校准的线程函数"""
        try:
            self.add_remote_log(f"🔍 查找校准脚本...")
            script_path = os.path.join(os.path.dirname(__file__), 'servo_quick_calibration.py')

            # 如果servo_quick_calibration.py不存在，尝试使用servo_middle_calibration.py
            if not os.path.exists(script_path):
                script_path = os.path.join(os.path.dirname(__file__), 'servo_middle_calibration.py')
                self.add_remote_log(f"⚠️ 未找到servo_quick_calibration.py，使用servo_middle_calibration.py")
                command = [sys.executable, script_path, port_name, "2"]  # 使用自动模式
            else:
                self.add_remote_log(f"✅ 找到校准脚本: servo_quick_calibration.py")
                command = [sys.executable, script_path, port_name]

            self.add_remote_log(f"🚀 启动校准进程: {' '.join(command)}")

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=os.path.dirname(__file__)
            )

            # 监控输出
            important_keywords = ["连接", "扫描", "校准", "完成", "失败", "错误", "成功", "发现"]
            while process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            print(f"[{port_name} CALIB] {line}")
                            # 只显示包含重要关键词的日志
                            if any(keyword in line for keyword in important_keywords):
                                self.add_remote_log(f"[{port_name}] {line}")
                except:
                    break

            return_code = process.wait()
            if return_code == 0:
                self.add_remote_log(f"✅ {port_name}中位校准完成 - 进程正常退出")
                self.status_bar.showMessage(f"{port_name}校准完成", 3000)
            else:
                self.add_remote_log(f"❌ {port_name}中位校准失败 - 退出码: {return_code}")
                self.status_bar.showMessage(f"{port_name}校准失败", 3000)

            # 重新启动相应端口的扫描线程
            self.add_remote_log(f"⏳ 等待端口释放...")
            import time
            time.sleep(1.0)  # 增加等待时间确保端口完全释放

            if port_name == self.left_port:
                self.left_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")
            elif port_name == self.right_port:
                self.right_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")

        except Exception as e:
            self.add_remote_log(f"❌ {port_name}校准异常: {e}")
            self.status_bar.showMessage(f"{port_name}校准异常: {e}", 3000)
            # 即使出现异常也要尝试重新启动扫描线程
            try:
                import time
                time.sleep(1.0)
                if port_name == self.left_port:
                    self.left_panel.worker.start()
                    self.add_remote_log(f"🔄 异常后重启{port_name}扫描线程")
                elif port_name == self.right_port:
                    self.right_panel.worker.start()
                    self.add_remote_log(f"🔄 异常后重启{port_name}扫描线程")
            except:
                self.add_remote_log(f"⚠️ 重启{port_name}扫描线程失败")

    def run_quick_test(self, port_name: str):
        """快速中位测试 - 非阻塞执行"""
        self.add_remote_log(f"🧪 开始{port_name}中位测试...")
        self.status_bar.showMessage(f"正在执行{port_name}中位测试...", 5000)

        # 先停止相应端口的工作线程，避免端口冲突
        if port_name == self.left_port and self.left_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备测试")
            self.left_panel.worker.stop()
        elif port_name == self.right_port and self.right_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备测试")
            self.right_panel.worker.stop()

        # 等待端口释放
        import time
        time.sleep(1.0)

        from threading import Thread
        thread = Thread(target=self._execute_quick_test, args=(port_name,))
        thread.daemon = True
        thread.start()

        self.add_remote_log(f"📝 {port_name}测试进程已启动，请等待执行完成")

    def _execute_quick_test(self, port_name: str):
        """执行快速中位测试的线程函数"""
        try:
            script_path = os.path.join(os.path.dirname(__file__), 'servo_center_test.py')
            command = [sys.executable, script_path, port_name]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=os.path.dirname(__file__)
            )

            # 监控输出
            while process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            print(f"[{port_name} TEST] {line}")
                except:
                    break

            return_code = process.wait()
            if return_code == 0:
                self.add_remote_log(f"✅ {port_name}中位测试完成")
            else:
                self.add_remote_log(f"❌ {port_name}中位测试失败")

            # 重新启动相应端口的扫描线程
            import time
            time.sleep(0.5)  # 等待端口完全释放

            if port_name == self.left_port:
                self.left_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")
            elif port_name == self.right_port:
                self.right_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")

        except Exception as e:
            self.add_remote_log(f"❌ {port_name}测试异常: {e}")
            # 即使出现异常也要尝试重新启动扫描线程
            try:
                import time
                time.sleep(0.5)
                if port_name == self.left_port:
                    self.left_panel.worker.start()
                elif port_name == self.right_port:
                    self.right_panel.worker.start()
            except:
                pass

    def run_quick_disable(self, port_name: str):
        """快速失能电机 - 非阻塞执行"""
        self.add_remote_log(f"⏹️ 开始{port_name}失能电机...")
        self.status_bar.showMessage(f"正在执行{port_name}失能电机...", 5000)

        # 先停止相应端口的工作线程，避免端口冲突
        if port_name == self.left_port and self.left_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备失能")
            self.left_panel.worker.stop()
        elif port_name == self.right_port and self.right_panel.worker.is_connected:
            self.add_remote_log(f"⏸️ 已停止{port_name}扫描线程，准备失能")
            self.right_panel.worker.stop()

        # 等待端口释放
        import time
        time.sleep(1.0)

        from threading import Thread
        thread = Thread(target=self._execute_quick_disable, args=(port_name,))
        thread.daemon = True
        thread.start()

        self.add_remote_log(f"📝 {port_name}失能进程已启动，请等待执行完成")

    def _execute_quick_disable(self, port_name: str):
        """执行快速失能电机的线程函数"""
        try:
            script_path = os.path.join(os.path.dirname(__file__), 'servo_disable.py')
            command = [sys.executable, script_path, port_name]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=os.path.dirname(__file__)
            )

            # 监控输出
            while process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            print(f"[{port_name} DISABLE] {line}")
                except:
                    break

            return_code = process.wait()
            if return_code == 0:
                self.add_remote_log(f"✅ {port_name}电机已失能，可手动旋转")
            else:
                self.add_remote_log(f"❌ {port_name}失能失败")

            # 重新启动相应端口的扫描线程
            import time
            time.sleep(0.5)  # 等待端口完全释放

            if port_name == self.left_port:
                self.left_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")
            elif port_name == self.right_port:
                self.right_panel.worker.start()
                self.add_remote_log(f"▶️ 已重新启动{port_name}扫描线程")

        except Exception as e:
            self.add_remote_log(f"❌ {port_name}失能异常: {e}")
            # 即使出现异常也要尝试重新启动扫描线程
            try:
                import time
                time.sleep(0.5)
                if port_name == self.left_port:
                    self.left_panel.worker.start()
                elif port_name == self.right_port:
                    self.right_panel.worker.start()
            except:
                pass

    def add_remote_log(self, message):
        """添加遥控日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[REMOTE] {message}"
        print(f"[REMOTE] {log_entry}")
        self.status_bar.showMessage(f"遥控: {message}", 3000)

    def on_remote_started(self):
        """遥控启动回调"""
        pass

    def on_remote_stopped(self):
        """遥控停止回调"""
        pass

    def refresh_ports(self):
        """刷新可用串口列表"""
        try:
            self.available_ports = get_available_ports()
            print(f"[DEBUG] Available ports: {self.available_ports}")

            # 保存当前选择
            current_left = self.left_port_combo.currentText() if hasattr(self, 'left_port_combo') else self.left_port
            current_right = self.right_port_combo.currentText() if hasattr(self, 'right_port_combo') else self.right_port

            # 清空下拉框
            self.left_port_combo.clear()
            self.right_port_combo.clear()

            # 添加可用串口
            for port in self.available_ports:
                self.left_port_combo.addItem(port)
                self.right_port_combo.addItem(port)

            # 尝试恢复之前的选择
            left_index = self.left_port_combo.findText(current_left)
            if left_index >= 0:
                self.left_port_combo.setCurrentIndex(left_index)
            elif self.left_port_combo.count() > 0:
                self.left_port_combo.setCurrentIndex(0)

            right_index = self.right_port_combo.findText(current_right)
            if right_index >= 0:
                self.right_port_combo.setCurrentIndex(right_index)
            elif self.right_port_combo.count() > 1:
                self.right_port_combo.setCurrentIndex(1)
            elif self.right_port_combo.count() > 0:
                self.right_port_combo.setCurrentIndex(0)

            self.status_bar.showMessage(f"串口列表已刷新 - 发现 {len(self.available_ports)} 个串口", 3000)

        except Exception as e:
            print(f"[DEBUG] Refresh ports error: {e}")
            self.status_bar.showMessage(f"刷新串口列表失败: {e}", 3000)

    def on_left_port_changed(self, port_name):
        """左串口选择改变"""
        if port_name and port_name != self.left_port:
            print(f"[DEBUG] Left port changed from {self.left_port} to {port_name}")
            self.left_port = port_name

            # 停止当前工作线程
            self.left_panel.stop()

            # 更新面板的端口名称和标题
            self.left_panel.update_port_name(self.left_port)

            # 创建新的工作线程
            self.left_panel.worker = ServoWorker(self.left_port, "left")

            # 重新连接信号
            self.left_panel.init_connections()

            # 启动新的工作线程
            self.left_panel.worker.start()

            self.status_bar.showMessage(f"串口1已切换到: {port_name}", 3000)

    def on_right_port_changed(self, port_name):
        """右串口选择改变"""
        if port_name and port_name != self.right_port:
            print(f"[DEBUG] Right port changed from {self.right_port} to {port_name}")
            self.right_port = port_name

            # 停止当前工作线程
            self.right_panel.stop()

            # 更新面板的端口名称和标题
            self.right_panel.update_port_name(self.right_port)

            # 创建新的工作线程
            self.right_panel.worker = ServoWorker(self.right_port, "right")

            # 重新连接信号
            self.right_panel.init_connections()

            # 启动新的工作线程
            self.right_panel.worker.start()

            self.status_bar.showMessage(f"串口2已切换到: {port_name}", 3000)

    def run_quick_calibration_left(self):
        """串口1快速中位校准"""
        self.run_quick_calibration(self.left_port)

    def run_quick_test_left(self):
        """串口1快速中位测试"""
        self.run_quick_test(self.left_port)

    def run_quick_disable_left(self):
        """串口1快速失能电机"""
        self.run_quick_disable(self.left_port)

    def run_quick_calibration_right(self):
        """串口2快速中位校准"""
        self.run_quick_calibration(self.right_port)

    def run_quick_test_right(self):
        """串口2快速中位测试"""
        self.run_quick_test(self.right_port)

    def run_quick_disable_right(self):
        """串口2快速失能电机"""
        self.run_quick_disable(self.right_port)

    def closeEvent(self, event):
        """关闭事件"""
        # 停止遥控操作
        if self.remote_worker and self.remote_worker.running:
            self.remote_worker.stop_remote_control()

        # 停止舵机标定操作
        self.left_panel.stop()
        self.right_panel.stop()

        super().closeEvent(event)


def get_available_ports():
    """获取可用串口列表"""
    try:
        import serial.tools.list_ports
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return sorted(ports)
    except ImportError:
        print("Warning: pyserial not available, using default ports")
        if platform.system() == "Windows":
            return ["COM1", "COM2"]
        else:
            return ["/dev/ttyUSB0", "/dev/ttyUSB1"]


def main():
    """主函数"""
    import platform
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='双串口工厂舵机标定工具')
    parser.add_argument('--port1', type=str, help='指定串口1 (例如: COM1 或 /dev/ttyUSB0)')
    parser.add_argument('--port2', type=str, help='指定串口2 (例如: COM2 或 /dev/ttyUSB1)')
    parser.add_argument('--list-ports', action='store_true', help='列出可用串口并退出')
    args = parser.parse_args()

    # 如果只是列出串口
    if args.list_ports:
        try:
            available_ports = get_available_ports()
            print("可用串口列表:")
            for i, port in enumerate(available_ports, 1):
                print(f"  {i}. {port}")
            if not available_ports:
                print("  未发现可用串口")
        except Exception as e:
            print(f"获取串口列表失败: {e}")
        return

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 根据操作系统选择默认端口
    system = platform.system()
    if system == "Windows":
        default_left_port = "COM1"
        default_right_port = "COM2"
    else:  # Linux - 支持USB转串口和ACM设备
        default_left_port = "/dev/ttyUSB0"  # USB转串口设备
        default_right_port = "/dev/ttyUSB1"
        # 如果USB设备不存在，系统会自动检测可用的ACM设备

    # 使用命令行参数或默认端口
    left_port = args.port1 if args.port1 else default_left_port
    right_port = args.port2 if args.port2 else default_right_port

    print(f"启动双串口工厂舵机标定工具")
    print(f"系统: {system}")
    print(f"串口1: {left_port}")
    print(f"串口2: {right_port}")

    # 检查可用端口
    try:
        available_ports = get_available_ports()
        print(f"检测到的可用串口: {available_ports}")

        # 如果没有指定命令行参数，自动选择最佳端口
        if not args.port1 or not args.port2:
            if system == "Windows":
                preferred_ports = ["COM1", "COM2"]
            else:  # Linux - 优先选择USB设备，然后是ACM设备
                preferred_ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]

            if len(available_ports) >= 2:
                # 查找首选端口
                found_ports = []
                for pref_port in preferred_ports:
                    if pref_port in available_ports:
                        found_ports.append(pref_port)

                # 如果找到两个首选端口，使用它们
                if len(found_ports) >= 2 and not args.port1 and not args.port2:
                    left_port, right_port = found_ports[0], found_ports[1]
                    print(f"使用首选端口: {left_port}, {right_port}")
                # 如果只找到一个首选端口
                elif len(found_ports) == 1:
                    if not args.port1:
                        left_port = found_ports[0]
                    if not args.port2:
                        # 选择一个不是首选端口的其他端口
                        for port in available_ports:
                            if port != (args.port1 or found_ports[0]):
                                right_port = port
                                break
                    print(f"使用混合端口配置: {left_port}, {right_port}")
                # 没有找到首选端口
                elif not args.port1 and not args.port2:
                    left_port, right_port = available_ports[0], available_ports[1]
                    print(f"使用前两个可用端口: {left_port}, {right_port}")

            elif len(available_ports) == 1:
                if not args.port1:
                    left_port = available_ports[0]
                if not args.port2:
                    right_port = default_right_port
                print(f"只有一个可用端口: {available_ports[0]}, 备用端口: {right_port}")
            else:
                print("未发现可用串口，使用默认配置")

    except Exception as e:
        print(f"检查可用端口时出错: {e}")

    # 创建并显示主窗口
    window = EZToolUI(left_port, right_port)
    window.show()

    print("UI界面已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()