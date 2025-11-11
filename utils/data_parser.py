#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTServo Data Parser Utility
数据解析工具模块
"""

import struct
from typing import List, Tuple, Dict, Any, Optional
from ..config.memory_map import MemoryMap, AddressNames


class DataParser:
    """数据解析器"""

    @staticmethod
    def bytes_to_int(data: bytes, signed: bool = False) -> int:
        """
        字节数组转换为整数

        Args:
            data: 字节数组
            signed: 是否为有符号数

        Returns:
            整数值
        """
        if not data:
            return 0

        fmt = f"{'>' if not data else '<'}{'h' if len(data) == 2 else 'i' if len(data) == 4 else 'b'}"
        if not signed:
            fmt = fmt.replace('h', 'H').replace('i', 'I').replace('b', 'B')

        try:
            return struct.unpack(fmt, data)[0]
        except struct.error:
            # 回退到手动解析
            result = 0
            for i, byte in enumerate(data):
                result |= byte << (8 * i)

            if signed and len(data) > 0 and (data[-1] & 0x80):
                # 有符号数，进行符号扩展
                result -= (1 << (8 * len(data)))

            return result

    @staticmethod
    def int_to_bytes(value: int, length: int, signed: bool = False) -> bytes:
        """
        整数转换为字节数组

        Args:
            value: 整数值
            length: 字节数组长度
            signed: 是否为有符号数

        Returns:
            字节数组
        """
        fmt = f"{'<' if length > 0 else '>'}{'h' if length == 2 else 'i' if length == 4 else 'b'}"
        if not signed:
            fmt = fmt.replace('h', 'H').replace('i', 'I').replace('b', 'B')

        try:
            return struct.pack(fmt, value)
        except struct.error:
            # 回退到手动转换
            result = bytearray(length)
            for i in range(length):
                result[i] = (value >> (8 * i)) & 0xFF
            return bytes(result)

    @staticmethod
    def parse_position(data: bytes) -> int:
        """解析位置数据 (2字节)"""
        return DataParser.bytes_to_int(data, signed=True)

    @staticmethod
    def parse_speed(data: bytes) -> int:
        """解析速度数据 (2字节)"""
        return DataParser.bytes_to_int(data, signed=True)

    @staticmethod
    def parse_current(data: bytes) -> int:
        """解析电流数据 (2字节)"""
        return DataParser.bytes_to_int(data, signed=True)

    @staticmethod
    def parse_torque(data: bytes) -> int:
        """解析扭矩数据 (2字节)"""
        return DataParser.bytes_to_int(data, signed=True)

    @staticmethod
    def parse_voltage(data: bytes) -> float:
        """解析电压数据 (1字节, 0.1V单位)"""
        return DataParser.bytes_to_int(data) / 10.0

    @staticmethod
    def parse_temperature(data: bytes) -> int:
        """解析温度数据 (1字节, 摄氏度)"""
        return DataParser.bytes_to_int(data)

    @staticmethod
    def format_position(value: int) -> str:
        """格式化位置显示"""
        return f"{value:4d} ({value/4095*100:5.1f}%)"

    @staticmethod
    def format_speed(value: int) -> str:
        """格式化速度显示"""
        return f"{value:5d} RPM"

    @staticmethod
    def format_current(value: int) -> str:
        """格式化电流显示"""
        return f"{value:4d} mA"

    @staticmethod
    def format_voltage(value: float) -> str:
        """格式化电压显示"""
        return f"{value:5.1f} V"

    @staticmethod
    def format_temperature(value: int) -> str:
        """格式化温度显示"""
        return f"{value:3d}°C"


class RegisterValue:
    """寄存器值封装"""

    def __init__(self, address: int, data: bytes, name: str = None):
        self.address = address
        self.data = data
        self.name = name or AddressNames.get_name(address)
        self.value = self._parse_value()
        self.formatted_value = self._format_value()

    def _parse_value(self) -> Any:
        """解析寄存器值"""
        if not self.data:
            return None

        length = len(self.data)
        if length == 1:
            return DataParser.bytes_to_int(self.data)
        elif length == 2:
            return DataParser.bytes_to_int(self.data, signed=True)
        elif length == 4:
            return DataParser.bytes_to_int(self.data, signed=True)
        else:
            return self.data

    def _format_value(self) -> str:
        """格式化显示值"""
        if self.value is None:
            return "N/A"

        # 根据寄存器地址进行特殊格式化
        if self.address in [MemoryMap.PRESENT_POSITION_L, MemoryMap.GOAL_POSITION_L]:
            if isinstance(self.data, bytes) and len(self.data) >= 2:
                pos = DataParser.parse_position(self.data)
                return DataParser.format_position(pos)

        elif self.address in [MemoryMap.PRESENT_SPEED_L, MemoryMap.GOAL_SPEED_L]:
            if isinstance(self.data, bytes) and len(self.data) >= 2:
                speed = DataParser.parse_speed(self.data)
                return DataParser.format_speed(speed)

        elif self.address in [MemoryMap.PRESENT_CURRENT_L]:
            if isinstance(self.data, bytes) and len(self.data) >= 2:
                current = DataParser.parse_current(self.data)
                return DataParser.format_current(current)

        elif self.address == MemoryMap.PRESENT_VOLTAGE:
            voltage = DataParser.parse_voltage(self.data)
            return DataParser.format_voltage(voltage)

        elif self.address == MemoryMap.PRESENT_TEMPERATURE:
            temp = DataParser.parse_temperature(self.data)
            return DataParser.format_temperature(temp)

        return str(self.value)

    def __str__(self) -> str:
        return f"{self.name} (0x{self.address:02X}): {self.formatted_value}"


class MemoryMapParser:
    """内存映射解析器"""

    def __init__(self):
        self.regions = {
            'eprom_readonly': (0, 4),
            'eprom_config': (5, 17),
            'eprom_advanced': (18, 45),
            'sram_control': (46, 56),
            'sram_status': (57, 69),
            'default_params': (80, 86)
        }

    def parse_memory_dump(self, dump_data: Dict[int, bytes]) -> Dict[str, List[RegisterValue]]:
        """
        解析内存转储数据

        Args:
            dump_data: 地址到数据的映射

        Returns:
            按区域分组的寄存器值列表
        """
        result = {}

        for region_name, (start_addr, end_addr) in self.regions.items():
            region_values = []
            for addr in range(start_addr, end_addr + 1):
                if addr in dump_data:
                    reg_value = RegisterValue(addr, dump_data[addr])
                    region_values.append(reg_value)

            result[region_name] = region_values

        return result

    def get_region_info(self, address: int) -> Optional[str]:
        """获取地址所属区域"""
        for region_name, (start_addr, end_addr) in self.regions.items():
            if start_addr <= address <= end_addr:
                return region_name
        return None

    def format_memory_table(self, values: List[RegisterValue]) -> str:
        """格式化内存值表格"""
        if not values:
            return "无数据"

        table = []
        table.append(f"{'地址':>6} | {'名称':>20} | {'原始数据':>20} | {'解析值':>15}")
        table.append("-" * 70)

        for reg_value in values:
            addr_str = f"0x{reg_value.address:02X}"
            data_str = reg_value.data.hex() if reg_value.data else "N/A"
            table.append(f"{addr_str:>6} | {reg_value.name:>20} | {data_str:>20} | {reg_value.formatted_value:>15}")

        return "\n".join(table)


# 全局解析器实例
data_parser = DataParser()
memory_parser = MemoryMapParser()