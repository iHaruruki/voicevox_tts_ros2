#!/usr/bin/env python3
import rclpy
from rclpy.action import ActionClient
from audio_generator.action import Tts

def main():
    rclpy.init()
    node = rclpy.create_node('tts_action_client_example')
    client = ActionClient(node, Tts, 'audio_generator')

    goal_msg = Tts.Goal()
    goal_msg.text = "アクションによる音声合成テストです。"
    goal_msg.speaker_id = 3
    goal_msg.speed = 1.0
    goal_msg.pitch = 0.0
    goal_msg.intonation = 1.0
    goal_msg.volume = 1.0
    goal_msg.play = True
    goal_msg.return_wav = False

    if not client.wait_for_server(timeout_sec=5.0):
        node.get_logger().error("Action server not available.")
        return

    send_future = client.send_goal_async(goal_msg, feedback_callback=lambda fb:
        node.get_logger().info(
            f"Feedback: phase={fb.feedback.phase_label} "
            f"progress={fb.feedback.progress:.2f} msg={fb.feedback.message}"
        )
    )

    def goal_response(fut):
        goal_handle = fut.result()
        if not goal_handle.accepted:
            node.get_logger().error("Goal rejected.")
            return
        node.get_logger().info("Goal accepted.")
        result_future = goal_handle.get_result_async()

        def result_cb(rf):
            res = rf.result().result
            node.get_logger().info(f"Result success={res.success} error={res.error} wav_len={len(res.wav_data)}")
            rclpy.shutdown()
        result_future.add_done_callback(result_cb)

    send_future.add_done_callback(goal_response)
    rclpy.spin(node)

if __name__ == "__main__":
    main()