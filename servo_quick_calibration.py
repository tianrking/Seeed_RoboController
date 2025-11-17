#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Middle Value Calibration - Disable servos and set current position as center
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
SMS_STS_CALIBRATE_MIDDLE_VALUE = 128

def quick_middle_calibration(port_name: str):
    """Quick calibration: disable all servos and set current positions as center"""
    print(f"Quick Middle Calibration: {port_name}")
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
        # Step 1: Disable all servos first
        print("Disabling all servos...")
        servo_ids = [1, 2, 3, 4, 5, 6]
        disabled_count = 0

        for servo_id in servo_ids:
            result, error = servo_handler.write1ByteTxRx(servo_id, SMS_STS_TORQUE_ENABLE, 0)
            if result == COMM_SUCCESS:
                disabled_count += 1
            time.sleep(0.05)

        print(f"+ {disabled_count} servos disabled")
        time.sleep(1)  # Wait for servos to stabilize

        # Step 2: Calibrate middle values for all servos
        print("Calibrating middle values...")
        calibrated_count = 0

        for servo_id in servo_ids:
            print(f"  Calibrating ID{servo_id}...")

            # Unlock EEPROM
            result, error = servo_handler.unLockEprom(servo_id)
            if result != COMM_SUCCESS:
                print(f"    EEPROM unlock failed: {error}")
                continue

            time.sleep(0.05)

            # Send calibration command (128 to Addr 40)
            result, error = servo_handler.write1ByteTxRx(servo_id, SMS_STS_TORQUE_ENABLE, SMS_STS_CALIBRATE_MIDDLE_VALUE)
            if result != COMM_SUCCESS:
                print(f"    Calibration failed: {error}")
                servo_handler.LockEprom(servo_id)
                continue

            time.sleep(0.05)

            # Lock EEPROM
            servo_handler.LockEprom(servo_id)
            calibrated_count += 1
            print(f"    + ID{servo_id} calibrated")

        print(f"+ {calibrated_count} servos calibrated successfully")
        print("Calibration complete!")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        port_handler.closePort()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_calibration.py <port_name>")
        sys.exit(1)

    port_name = sys.argv[1]
    success = quick_middle_calibration(port_name)
    sys.exit(0 if success else 1)