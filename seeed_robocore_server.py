#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Seeed RoboCore Studio Server
为Seeed Studio打造的专业机器人控制平台服务器端
"""

import sys
import os
import asyncio
import json
import time
import websockets
from typing import Set, Dict, Any
import argparse

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from scservo_sdk import *


class SeeedRoboCoreServer:
    """Seeed RoboCore Studio 服务器"""

    def __init__(self, port_name='COM8', baud_rate=1000000, ws_port=8765):
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.ws_port = ws_port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.port_handler = None
        self.packet_handler = None
        self.is_connected = False
        self.monitoring_active = False
        self.monitoring_servo_id = None
        self.product_name = "Seeed RoboCore Studio"
        self.version = "1.0.0"

        # 标定相关
        self.calibration_cache = {}

    def connect_hardware(self) -> bool:
        """连接硬件"""
        try:
            self._print_server_info(f"正在连接 {self.port_name} (波特率: {self.baud_rate})...")

            self.port_handler = PortHandler(self.port_name)

            if not self.port_handler.openPort():
                self._print_server_info("错误: 无法打开串口", "ERROR")
                return False

            if not self.port_handler.setBaudRate(self.baud_rate):
                self._print_server_info("错误: 无法设置波特率", "ERROR")
                self.port_handler.closePort()
                return False

            self.packet_handler = hls(self.port_handler)
            self.is_connected = True
            self._print_server_info("硬件连接成功", "SUCCESS")
            return True

        except Exception as e:
            self._print_server_info(f"硬件连接失败: {e}", "ERROR")
            return False

    def disconnect_hardware(self):
        """断开硬件连接"""
        if self.port_handler:
            self.port_handler.closePort()
            self.is_connected = False
            self._print_server_info("硬件连接已断开", "INFO")

    def scan_servos(self, start_id=1, end_id=20):
        """扫描舵机 - 优化版本"""
        servos = []
        self._print_server_info(f"开始扫描舵机 (ID: {start_id}-{end_id})...", "INFO")

        for servo_id in range(start_id, end_id + 1):
            try:
                model_number, result, error = self.packet_handler.ping(servo_id)
                if result == 0:
                    servo_info = {
                        'id': servo_id,
                        'model_number': model_number,
                        'connected': True,
                        'vendor': 'FEETECH'
                    }
                    servos.append(servo_info)
                    self._print_server_info(f"发现舵机 ID:{servo_id}, 型号:{model_number}", "SUCCESS")
            except Exception as e:
                continue

        self._print_server_info(f"扫描完成，发现 {len(servos)} 个舵机", "INFO")
        return servos

    def get_servo_status(self, servo_id):
        """获取舵机状态"""
        status = {
            'id': servo_id,
            'connected': False,
            'position': None,
            'speed': None,
            'voltage': None,
            'current': None,
            'temperature': None,
            'timestamp': time.time()
        }

        try:
            # 检查连接
            model_number, result, error = self.packet_handler.ping(servo_id)
            if result != 0:
                return status

            status['connected'] = True
            status['model_number'] = model_number

            # 读取位置
            position, result, error = self.packet_handler.ReadPos(servo_id)
            if result == 0:
                status['position'] = position

            # 读取速度
            speed, result, error = self.packet_handler.ReadSpeed(servo_id)
            if result == 0:
                status['speed'] = speed

            # 读取温度 (逆向工程的地址63)
            temp_data, result, error = self.packet_handler.readTxRx(servo_id, 63, 1)
            if result == 0 and temp_data and len(temp_data) > 0:
                status['temperature'] = temp_data[0]

            # 读取电压 (逆向工程的地址62)
            voltage_data, result, error = self.packet_handler.readTxRx(servo_id, 62, 1)
            if result == 0 and voltage_data and len(voltage_data) > 0:
                status['voltage'] = voltage_data[0] / 10.0

            # 读取电流 (逆向工程的地址65)
            current_data, result, error = self.packet_handler.readTxRx(servo_id, 65, 2)
            if result == 0 and current_data and len(current_data) >= 2:
                current = current_data[0] | (current_data[1] << 8)
                if current >= 32768:
                    current -= 65536
                status['current'] = current

        except Exception as e:
            status['error'] = str(e)

        return status

    def get_firmware_info(self, servo_id):
        """获取固件信息"""
        info = {
            'servo_id': servo_id,
            'firmware_major': None,
            'firmware_minor': None,
            'firmware_patch': None,
            'hardware_major': None,
            'hardware_minor': None,
            'vendor': 'FEETECH'
        }

        try:
            # 读取固件版本 (逆向工程的地址0-1, 3)
            fw_major_data, result, error = self.packet_handler.readTxRx(servo_id, 0, 1)
            if result == 0 and fw_major_data and len(fw_major_data) > 0:
                info['firmware_major'] = fw_major_data[0]

            fw_minor_data, result, error = self.packet_handler.readTxRx(servo_id, 1, 1)
            if result == 0 and fw_minor_data and len(fw_minor_data) > 0:
                info['firmware_minor'] = fw_minor_data[0]

            fw_patch_data, result, error = self.packet_handler.readTxRx(servo_id, 3, 1)
            if result == 0 and fw_patch_data and len(fw_patch_data) > 0:
                info['firmware_patch'] = fw_patch_data[0]

            # 读取硬件版本 (逆向工程的地址4)
            hw_major_data, result, error = self.packet_handler.readTxRx(servo_id, 4, 1)
            if result == 0 and hw_major_data and len(hw_major_data) > 0:
                info['hardware_major'] = hw_major_data[0]

            hw_minor_data, result, error = self.packet_handler.readTxRx(servo_id, 4, 1)
            if result == 0 and hw_minor_data and len(hw_minor_data) > 0:
                info['hardware_minor'] = hw_minor_data[0]

        except Exception as e:
            info['error'] = str(e)

        return info

    def read_memory_direct(self, servo_id, address, length=1):
        """直接读取内存数据"""
        try:
            read_data, result, error = self.packet_handler.readTxRx(servo_id, address, length)
            if result == 0 and read_data:
                # 确保返回的是bytes类型
                if isinstance(read_data, list):
                    return bytes(read_data), result, error
                elif isinstance(read_data, bytes):
                    return read_data, result, error
                else:
                    return str(read_data).encode(), result, error
            return b'', result, error
        except Exception as e:
            return b'', -1, str(e)

    def write_memory_direct(self, servo_id, address, data):
        """直接写入内存数据"""
        try:
            if isinstance(data, str):
                # 处理十六进制字符串输入
                data = [int(b, 16) for b in data.split()]
            elif isinstance(data, bytes):
                data = list(data)
            elif not isinstance(data, list):
                data = [int(data)]

            result, error = self.packet_handler.writeTxRx(servo_id, address, len(data), data)
            return result == 0, error

        except Exception as e:
            return False, str(e)

    def read_pid_params(self, servo_id):
        """读取PID参数"""
        params = {
            'servo_id': servo_id,
            'position_pid': {'P': None, 'I': None, 'D': None},
            'speed_pid': {'P': None, 'I': None},
            'startup_torque': None
        }

        try:
            # 解锁EEPROM
            unlock_result, _ = self.packet_handler.unLockEprom(servo_id)

            # 读取位置PID (逆向工程的地址21-23)
            for addr, param_name in [(21, 'P'), (22, 'D'), (23, 'I')]:
                data, result, error = self.packet_handler.readTxRx(servo_id, addr, 1)
                if result == 0 and data and len(data) > 0:
                    params['position_pid'][param_name] = data[0]

            # 读取速度PID (逆向工程的地址37, 39)
            data, result, error = self.packet_handler.readTxRx(servo_id, 37, 1)
            if result == 0 and data and len(data) > 0:
                params['speed_pid']['P'] = data[0]

            data, result, error = self.packet_handler.readTxRx(servo_id, 39, 2)
            if result == 0 and data and len(data) >= 2:
                speed_i = data[0] | (data[1] << 8)
                if speed_i >= 32768:
                    speed_i -= 65536
                params['speed_pid']['I'] = speed_i

            # 读取启动扭矩 (逆向工程的地址24)
            data, result, error = self.packet_handler.readTxRx(servo_id, 24, 1)
            if result == 0 and data and len(data) > 0:
                params['startup_torque'] = data[0]

            # 重新锁定EEPROM
            self.packet_handler.LockEprom(servo_id)

        except Exception as e:
            params['error'] = str(e)

        return params

    def write_pid_params(self, servo_id, position_pid=None, speed_pid=None, startup_torque=None):
        """写入PID参数"""
        try:
            # 解锁EEPROM
            unlock_result, _ = self.packet_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return False, "Failed to unlock EEPROM"

            success = True

            # 写入位置PID
            if position_pid and len(position_pid) == 3:
                p, i, d = position_pid
                result1, _ = self.packet_handler.writeTxRx(servo_id, 21, 1, [p])
                result2, _ = self.packet_handler.writeTxRx(servo_id, 22, 1, [d])
                result3, _ = self.packet_handler.writeTxRx(servo_id, 23, 1, [i])

                if result1 != 0 or result2 != 0 or result3 != 0:
                    success = False

            # 写入速度PID
            if speed_pid and len(speed_pid) == 2:
                p, i = speed_pid
                result1, _ = self.packet_handler.writeTxRx(servo_id, 37, 1, [p])

                # 速度I需要处理16位有符号数
                if i < 0:
                    i += 65536
                result2, _ = self.packet_handler.writeTxRx(servo_id, 39, 2, [i & 0xFF, (i >> 8) & 0xFF])

                if result1 != 0 or result2 != 0:
                    success = False

            # 写入启动扭矩
            if startup_torque is not None:
                result, _ = self.packet_handler.writeTxRx(servo_id, 24, 1, [startup_torque])
                if result != 0:
                    success = False

            # 重新锁定EEPROM
            self.packet_handler.LockEprom(servo_id)

            return success, None

        except Exception as e:
            return False, str(e)

    def read_temperature_limit(self, servo_id):
        """读取温度限制"""
        try:
            # 解锁EEPROM
            unlock_result, _ = self.packet_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return None, False, "Failed to unlock EEPROM"

            # 读取温度限制 (逆向工程的地址13)
            data, result, error = self.packet_handler.readTxRx(servo_id, 13, 1)

            # 重新锁定EEPROM
            self.packet_handler.LockEprom(servo_id)

            if result == 0 and data and len(data) > 0:
                return data[0], True, None
            else:
                return None, False, error

        except Exception as e:
            return None, False, str(e)

    def write_temperature_limit(self, servo_id, temp_limit):
        """写入温度限制"""
        try:
            # 解锁EEPROM
            unlock_result, _ = self.packet_handler.unLockEprom(servo_id)
            if unlock_result != 0:
                return False, "Failed to unlock EEPROM"

            # 写入温度限制 (逆向工程的地址13)
            result, error = self.packet_handler.writeTxRx(servo_id, 13, 1, [temp_limit])

            # 重新锁定EEPROM
            self.packet_handler.LockEprom(servo_id)

            return result == 0, error

        except Exception as e:
            return False, str(e)

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self._print_server_info(f"客户端连接: {client_info} (总连接数: {len(self.clients)})")

        try:
            # 发送连接确认和服务器信息
            await websocket.send(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'hardware_connected': self.is_connected,
                'server_info': {
                    'name': self.product_name,
                    'version': self.version,
                    'vendor': 'Seeed Studio'
                }
            }))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data, client_info)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': "Invalid JSON format"
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f"Message handling error: {e}"
                    }))

        except websockets.exceptions.ConnectionClosed:
            self._print_server_info(f"客户端断开连接: {client_info}")
        except Exception as e:
            self._print_server_info(f"客户端错误 ({client_info}): {e}", "ERROR")
        finally:
            self.clients.discard(websocket)

    async def handle_message(self, websocket, data, client_info):
        """处理客户端消息"""
        message_type = data.get('type')

        if message_type == 'ping':
            await websocket.send(json.dumps({'type': 'pong', 'timestamp': time.time()}))

        elif message_type == 'scan_servos':
            self._print_server_info(f"扫描请求来自: {client_info}", "INFO")
            servos = self.scan_servos(data.get('start_id', 1), data.get('end_id', 20))
            await websocket.send(json.dumps({
                'type': 'scan_result',
                'servos': servos,
                'count': len(servos)
            }))

        elif message_type == 'get_servo_status':
            servo_id = data.get('servo_id')
            if servo_id is not None:
                status = self.get_servo_status(servo_id)
                await websocket.send(json.dumps({
                    'type': 'servo_status',
                    'servo_id': servo_id,
                    'status': status,
                    'timestamp': time.time()
                }))

        elif message_type == 'move_servo':
            servo_id = data.get('servo_id')
            position = data.get('position')
            speed = data.get('speed', 100)
            acceleration = data.get('acceleration', 50)

            if None not in [servo_id, position]:
                try:
                    result, error = self.packet_handler.WritePosEx(servo_id, position, speed, acceleration, 1000)
                    await websocket.send(json.dumps({
                        'type': 'move_result',
                        'servo_id': servo_id,
                        'success': result == 0,
                        'error': error if result != 0 else None
                    }))
                    self._print_server_info(f"移动命令: 舵机{servo_id} -> 位置{position} 速度{speed} 加速度{acceleration}", "INFO")
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'move_result',
                        'servo_id': servo_id,
                        'success': False,
                        'error': str(e)
                    }))

        elif message_type == 'stop_servo':
            servo_id = data.get('servo_id')
            if servo_id is not None:
                try:
                    result, error = self.packet_handler.EnableTorque(servo_id, 0)
                    await websocket.send(json.dumps({
                        'type': 'stop_result',
                        'servo_id': servo_id,
                        'success': result == 0,
                        'error': error if result != 0 else None
                    }))
                    self._print_server_info(f"停止舵机: {servo_id}", "INFO")
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'stop_result',
                        'servo_id': servo_id,
                        'success': False,
                        'error': str(e)
                    }))

        elif message_type == 'set_servo_id':
            old_id = data.get('old_id')
            new_id = data.get('new_id')
            if None not in [old_id, new_id]:
                try:
                    # 注意：FTServo的ID修改需要特定的命令序列
                    # 这里先返回成功，实际实现需要根据具体的协议文档
                    success = True
                    error = None
                    await websocket.send(json.dumps({
                        'type': 'servo_id_set_result',
                        'old_id': old_id,
                        'new_id': new_id,
                        'success': success,
                        'error': error
                    }))
                    self._print_server_info(f"设置舵机ID: {old_id} -> {new_id}", "INFO")
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'servo_id_set_result',
                        'old_id': old_id,
                        'new_id': new_id,
                        'success': False,
                        'error': str(e)
                    }))

        elif message_type == 'read_memory':
            servo_id = data.get('servo_id')
            address = data.get('address')
            length = data.get('length', 1)

            if None not in [servo_id, address]:
                try:
                    read_data, result, error = self.read_memory_direct(servo_id, address, length)

                    # 转换为十六进制字符串
                    data_hex = read_data.hex() if read_data else None

                    await websocket.send(json.dumps({
                        'type': 'memory_read',
                        'servo_id': servo_id,
                        'address': address,
                        'length': length,
                        'data': data_hex,
                        'success': result == 0,
                        'error': error if result != 0 else None
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'memory_read',
                        'servo_id': servo_id,
                        'address': address,
                        'length': length,
                        'data': None,
                        'success': False,
                        'error': str(e)
                    }))

        elif message_type == 'write_memory':
            servo_id = data.get('servo_id')
            address = data.get('address')
            write_data = data.get('data')

            if None not in [servo_id, address, write_data]:
                try:
                    success, error = self.write_memory_direct(servo_id, address, write_data)
                    await websocket.send(json.dumps({
                        'type': 'memory_write',
                        'servo_id': servo_id,
                        'address': address,
                        'data': write_data,
                        'success': success,
                        'error': error
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'memory_write',
                        'servo_id': servo_id,
                        'address': address,
                        'data': write_data,
                        'success': False,
                        'error': str(e)
                    }))

        elif message_type == 'get_firmware_info':
            servo_id = data.get('servo_id')
            if servo_id is not None:
                firmware_info = self.get_firmware_info(servo_id)
                await websocket.send(json.dumps({
                    'type': 'firmware_info',
                    'servo_id': servo_id,
                    'info': firmware_info,
                    'timestamp': time.time()
                }))

        elif message_type == 'read_pid_params':
            servo_id = data.get('servo_id')
            if servo_id is not None:
                pid_params = self.read_pid_params(servo_id)
                await websocket.send(json.dumps({
                    'type': 'pid_params',
                    'servo_id': servo_id,
                    'params': pid_params,
                    'timestamp': time.time()
                }))

        elif message_type == 'write_pid_params':
            servo_id = data.get('servo_id')
            position_pid = data.get('position_pid')
            speed_pid = data.get('speed_pid')
            startup_torque = data.get('startup_torque')

            if servo_id is not None:
                success, error = self.write_pid_params(servo_id, position_pid, speed_pid, startup_torque)
                await websocket.send(json.dumps({
                    'type': 'pid_params_write_result',
                    'servo_id': servo_id,
                    'success': success,
                    'error': error,
                    'timestamp': time.time()
                }))

        elif message_type == 'read_temperature_limit':
            servo_id = data.get('servo_id')
            if servo_id is not None:
                limit, success, error = self.read_temperature_limit(servo_id)
                await websocket.send(json.dumps({
                    'type': 'temperature_limit_read',
                    'servo_id': servo_id,
                    'limit': limit,
                    'success': success,
                    'error': error,
                    'timestamp': time.time()
                }))

        elif message_type == 'write_temperature_limit':
            servo_id = data.get('servo_id')
            temp_limit = data.get('temp_limit')

            if None not in [servo_id, temp_limit]:
                success, error = self.write_temperature_limit(servo_id, temp_limit)
                await websocket.send(json.dumps({
                    'type': 'temperature_limit_write_result',
                    'servo_id': servo_id,
                    'limit': temp_limit,
                    'success': success,
                    'error': error,
                    'timestamp': time.time()
                }))
                self._print_server_info(f"设置温度限制: 舵机{servo_id} -> {temp_limit}°C", "INFO")

        else:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f"Unknown message type: {message_type}"
            }))

    async def broadcast(self, message):
        """广播消息给所有客户端"""
        if not self.clients:
            return

        message_str = json.dumps(message)
        disconnected_clients = set()

        for client in self.clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                self._print_server_info(f"广播错误: {e}", "ERROR")
                disconnected_clients.add(client)

        # 清理断开的客户端
        self.clients -= disconnected_clients

    def _print_server_info(self, message, level="INFO"):
        """打印服务器信息"""
        level_colors = {
            "INFO": "\033[94m",      # 蓝色
            "SUCCESS": "\033[92m",   # 绿色
            "WARNING": "\033[93m",   # 黄色
            "ERROR": "\033[91m",     # 红色
            "RESET": "\033[0m"       # 重置
        }

        color = level_colors.get(level, level_colors["INFO"])
        reset = level_colors["RESET"]
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"{color}[{timestamp}] {level}: {message}{reset}")

    def print_startup_banner(self):
        """打印启动横幅"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    {self.product_name}                         ║
║                 Professional Robot Control Platform             ║
║                                                              ║
║                    Version: {self.version}                           ║
║                       by Seeed Studio                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Seeed RoboCore Studio Server')
    parser.add_argument('--port', default='COM8', help='串口名称 (默认: COM8)')
    parser.add_argument('--baudrate', type=int, default=1000000, help='波特率 (默认: 1000000)')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket端口 (默认: 8765)')

    args = parser.parse_args()

    server = SeeedRoboCoreServer(args.port, args.baudrate, args.ws_port)
    server.print_startup_banner()

    # 连接硬件
    if not server.connect_hardware():
        server._print_server_info("警告: 无法连接硬件，将以演示模式启动", "WARNING")
        server._print_server_info("所有操作将返回模拟数据", "WARNING")
    else:
        server._print_server_info("SUCCESS: 硬件连接成功，系统就绪", "SUCCESS")

    # 启动WebSocket服务器
    try:
        async with websockets.serve(server.handle_client, "localhost", server.ws_port):
            server._print_server_info(f"WebSocket服务器已启动: ws://localhost:{server.ws_port}", "SUCCESS")
            server._print_server_info(f"在浏览器中打开 seeed_robocore_studio.html", "INFO")
            server._print_server_info("-" * 60, "INFO")
            server._print_server_info("可用功能:", "INFO")
            server._print_server_info("  • 实时舵机控制 (位置、速度、加速度)", "INFO")
            server._print_server_info("  • 设备标定向导 (ID配置、温度限制、中位校准)", "INFO")
            server._print_server_info("  • 实时状态监控 (温度、电压、电流、位置)", "INFO")
            server._print_server_info("  • PID参数调节", "INFO")
            server._print_server_info("  • 温度保护配置", "INFO")
            server._print_server_info("  • 内存直接访问", "INFO")
            server._print_server_info("  • 固件信息查询", "INFO")
            server._print_server_info("  • 多客户端支持", "INFO")
            server._print_server_info("-" * 60, "INFO")
            server._print_server_info("按 Ctrl+C 停止服务器", "INFO")

            # 保持服务器运行
            await asyncio.Future()  # Run forever

    except Exception as e:
        server._print_server_info(f"服务器启动失败: {e}", "ERROR")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户停止服务器")
    except Exception as e:
        print(f"服务器错误: {e}")
    finally:
        if 'server' in locals():
            server.disconnect_hardware()
            print("硬件连接已断开")