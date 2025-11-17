#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Motor Disable - Set torque to 0 for all servos so they can be manually rotated
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

def quick_motor_disable(port_name: str):
    """Quick disable: set torque to 0 for all servos"""
    print(f"Quick Motor Disable: {port_name}")
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
        # Disable torque on all servos
        print("Disabling torque on all servos...")
        servo_ids = [1, 2, 3, 4, 5, 6]
        disabled_count = 0

        for servo_id in servo_ids:
            print(f"  Disabling ID{servo_id}...")
            result, error = servo_handler.write1ByteTxRx(servo_id, SMS_STS_TORQUE_ENABLE, 0)
            if result == COMM_SUCCESS:
                disabled_count += 1
                print(f"    + ID{servo_id} torque disabled")
            else:
                print(f"    X ID{servo_id} failed: {error}")
            time.sleep(0.05)

        print(f"+ {disabled_count}/{len(servo_ids)} servos disabled")
        print("All servos can now be manually rotated!")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        port_handler.closePort()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_disable.py <port_name>")
        sys.exit(1)

    port_name = sys.argv[1]
    success = quick_motor_disable(port_name)
    sys.exit(0 if success else 1)