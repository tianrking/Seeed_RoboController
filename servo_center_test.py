#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Middle Test - Enable servos and move to 2047 position to test calibration
Non-blocking version for GUI integration
"""

import sys
import os
import time

# Add SCServo SDK path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append('.')
sys.path.append('..')
sys.path.append('../scservo_sdk')
sys.path.append('../../')

try:
    from scservo_sdk.port_handler import PortHandler
    from scservo_sdk.sms_sts import sms_sts
    from scservo_sdk.scservo_def import COMM_SUCCESS
except ImportError as e:
    print(f"Error: Cannot import SCServo SDK: {e}")
    sys.exit(1)

# Register addresses
SMS_STS_TORQUE_ENABLE = 40

def quick_middle_test(port_name: str):
    """Quick test: enable servos and move to 2047"""
    print(f"Quick Middle Test: {port_name}")
    print("=" * 40)

    port_handler = PortHandler(port_name)
    if not port_handler.openPort():
        print(f"Cannot open {port_name}")
        return False
    if not port_handler.setBaudRate(1000000):
        print(f"Cannot set baud rate for {port_name}")
        port_handler.closePort()
        return False

    servo_handler = sms_sts(port_handler)

    try:
        # Step 1: Read current positions before movement
        print("Reading current positions...")
        servo_ids = [1, 2, 3, 4, 5, 6]
        positions_before = {}

        for servo_id in servo_ids:
            position, result, error = servo_handler.ReadPos(servo_id)
            if result == COMM_SUCCESS:
                positions_before[servo_id] = position
                degrees = position * 360.0 / 4095.0
                print(f"  ID{servo_id}: {position:4d} ({degrees:6.1f}°)")
            time.sleep(0.05)

        # Step 2: Enable torque on all servos
        print("Enabling torque...")
        enabled_count = 0

        for servo_id in servo_ids:
            result, error = servo_handler.write1ByteTxRx(servo_id, SMS_STS_TORQUE_ENABLE, 1)
            if result == COMM_SUCCESS:
                enabled_count += 1
            time.sleep(0.05)

        print(f"+ {enabled_count} servos enabled")
        time.sleep(1)  # Wait for torque to stabilize

        # Step 3: Move all servos to 2047 (middle position)
        print("Moving all servos to 2047...")
        moved_count = 0

        for servo_id in servo_ids:
            result, error = servo_handler.WritePosEx(servo_id, 2047, 1000, 50)
            if result == COMM_SUCCESS:
                moved_count += 1
            time.sleep(0.05)

        print(f"+ {moved_count} servos commanded to 2047")
        print("Waiting 3 seconds for movement...")
        time.sleep(3)

        # Step 4: Read final positions
        print("Reading final positions...")
        for servo_id in servo_ids:
            final_position, result, error = servo_handler.ReadPos(servo_id)
            if result == COMM_SUCCESS and servo_id in positions_before:
                movement = final_position - positions_before[servo_id]
                movement_degrees = movement * 360.0 / 4095.0
                final_degrees = final_position * 360.0 / 4095.0
                print(f"  ID{servo_id}: {final_position:4d} ({final_degrees:6.1f}°) [movement: {movement:+4d} ({movement_degrees:+5.1f}°)]")
            time.sleep(0.05)

        print("Test complete!")
        print("If servos stayed near their original positions, calibration is working correctly.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Keep torque enabled for observation
        print("Keeping torque enabled for observation...")
        time.sleep(2)
        port_handler.closePort()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_test.py <port_name>")
        sys.exit(1)

    port_name = sys.argv[1]
    success = quick_middle_test(port_name)
    sys.exit(0 if success else 1)