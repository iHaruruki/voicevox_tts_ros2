import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from voicevox_tts_interface_ros2.action import SpeakText
import time

class TTSClient(Node):
    def __init__(self):
        super().__init__('tts_action_client')
        self._client = ActionClient(self, SpeakText, 'speak_text')

    def send_goal(self, text: str, cancel_after_sec: float = 0.0):
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Action server not available.")
            return

        goal_msg = SpeakText.Goal()
        goal_msg.text = text
        goal_msg.speaker_id = -1        # -1 = サーバ既定
        goal_msg.playback = True
        goal_msg.speed = 0.0            # 0.0 = 既定維持
        goal_msg.pitch = 0.0
        goal_msg.intonation = 0.0
        goal_msg.volume = 0.0
        goal_msg.allow_cache = True     # キャッシュ許可

        self.get_logger().info("Sending goal...")
        send_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_cb
        )
        send_future.add_done_callback(
            lambda f: self.goal_response_cb(f, cancel_after_sec)
        )

    def goal_response_cb(self, future, cancel_after_sec: float):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("Goal rejected.")
            return
        self.get_logger().info("Goal accepted.")

        if cancel_after_sec > 0:
            self.get_logger().info(f"Will cancel after {cancel_after_sec}s")
            self.create_timer(cancel_after_sec, lambda: self.request_cancel(goal_handle))

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_cb)

    def feedback_cb(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(
            f"Feedback: state={fb.state} progress={fb.progress:.2f} excerpt='{fb.excerpt}'"
        )

    def request_cancel(self, goal_handle):
        if goal_handle.is_active:
            self.get_logger().info("Requesting cancel...")
            goal_handle.cancel_goal_async()

    def result_cb(self, future):
        result = future.result().result
        status = future.result().status
        self.get_logger().info(
            f"Result: success={result.success} status_code={status} "
            f"elapsed_ms={result.elapsed_ms} cache={result.from_cache} path={result.saved_path}"
        )
        # 全処理終わったらノード停止
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = TTSClient()
    node.send_goal("アクションクライアントテストです。", cancel_after_sec=0.0)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()