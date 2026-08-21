import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from pathlib import Path

FILE = Path.home() / 'ros2_ws/src/voicevox_tts_ros2/speech_script/speech1.txt'

class OncePublisher(Node):
    def __init__(self):
        super().__init__('once_publisher')
        self.pub = self.create_publisher(String, '/voicevox_tts_text', 10)
        text = Path(FILE).read_text(encoding='utf-8')
        msg = String()
        msg.data = text
        self.pub.publish(msg)
        self.get_logger().info('Published text.txt')
        rclpy.shutdown()

def main():
    rclpy.init()
    node = OncePublisher()
    if rclpy.ok():
        rclpy.spin(node)
    node.destroy_node()

if __name__ == '__main__':
    main()