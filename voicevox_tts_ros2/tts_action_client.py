import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from voicevox_tts_interface_ros2.action import SpeakText


class SpeakTextActionClient(Node):
    def __init__(self):
        super().__init__('speak_text_action_client')
        self._client = ActionClient(self, SpeakText, 'speak_text')

    def send_goal(
        self,
        text: str,
        speaker_id: int = -1,
        playback: bool = True,
        speed: float = 0.0,
        pitch: float = 0.0,
        intonation: float = 0.0,
        volume: float = 0.0,
        allow_cache: bool = True,
    ):
        """サーバに SpeakText ゴールを送信する"""

        goal_msg = SpeakText.Goal()
        goal_msg.text = text
        goal_msg.speaker_id = int(speaker_id)
        goal_msg.playback = bool(playback)
        goal_msg.speed = float(speed)
        goal_msg.pitch = float(pitch)
        goal_msg.intonation = float(intonation)
        goal_msg.volume = float(volume)
        goal_msg.allow_cache = bool(allow_cache)

        self.get_logger().info("Waiting for action server 'speak_text'...")
        self._client.wait_for_server()
        self.get_logger().info("Action server available, sending goal")

        send_goal_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected :(')
            rclpy.shutdown()
            return

        self.get_logger().info('Goal accepted :)')
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f"[Feedback] state={feedback.state} "
            f"progress={feedback.progress:.2f} "
            f"remaining_queue={feedback.remaining_queue} "
            f"excerpt='{feedback.excerpt}'"
        )

    def get_result_callback(self, future):
        result = future.result().result
        # ここは「引数 1 個だけ」にすること
        msg = (
            "[Result] success=%s error='%s' saved_path='%s' "
            "from_cache=%s elapsed_ms=%d used_speaker_id=%d"
        ) % (
            result.success,
            result.error_message,
            result.saved_path,
            result.from_cache,
            result.elapsed_ms,
            result.used_speaker_id,
        )
        self.get_logger().info(msg)
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = SpeakTextActionClient()

    # 簡易デモ
    demo_text = "Action クライアントからのテストです。"
    node.send_goal(
        text=demo_text,
        speaker_id=-1,     # -1 -> サーバ既定話者
        playback=True,     # True -> 再生あり
        speed=0.0,         # 0.0 -> サーバ既定 speed
        pitch=0.0,         # 0.0 -> サーバ既定 pitch
        intonation=0.0,    # 0.0 -> サーバ既定 intonation
        volume=0.0,        # 0.0 -> サーバ既定 volume
        allow_cache=True,  # True -> キャッシュ利用・保存
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()