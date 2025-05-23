#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import time

class AOPRNode(Node):
    def __init__(self):
        super().__init__('aopr_node')
        # Declare parameters for the serial port and baud rate
        self.declare_parameter('serial_port', '/dev/ttyAMA0')
        self.declare_parameter('baud_rate', 9600)
        serial_port = self.get_parameter('serial_port').value
        baud_rate = self.get_parameter('baud_rate').value

        # Open serial port
        try:
            self.ser = serial.Serial(serial_port, baud_rate, timeout=1)
            self.get_logger().info(f'Opened serial port {serial_port} at {baud_rate} baud.')
        except Exception as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            raise

        # Subscribe to /cmd_vel
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        self.get_logger().info('AOPR node started and listening to /cmd_vel.')

    def cmd_vel_callback(self, msg):
        # For a differential drive: left_speed & right_speed
        linear = msg.linear.x
        angular = msg.angular.z

        # Basic mixing: adjust as needed for your robot’s geometry
        left_speed = linear - angular
        right_speed = linear + angular

        # Convert speeds from -1..1 to Sabertooth's range:
        # For Motor 1 (left): mapping from [-1, 1] to [1, 127] with 0 --> 64.
        left_cmd = int(63 * left_speed + 64)
        # For Motor 2 (right): mapping from [-1, 1] to [128, 255] with 0 --> 192.
        right_cmd = int(63 * right_speed + 192)

        # Clamp the values to their respective ranges
        left_cmd = max(1, min(127, left_cmd))
        right_cmd = max(128, min(255, right_cmd))

        # Build & send the commands for each channel (simplified serial)
        try:
            m1_cmd = bytes([0x00, left_cmd])    # Motor 1 (Channel 1)
            m2_cmd = bytes([0x04, right_cmd])   # Motor 2 (Channel 2)
            
            self.ser.write(m1_cmd)
            time.sleep(0.01)
            self.ser.write(m2_cmd)
            self.get_logger().info(f'M1: {left_cmd}, M2: {right_cmd}')
        except Exception as e:
            self.get_logger().error(f'Error writing to serial port: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = AOPRNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down AOPR node.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
