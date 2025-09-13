import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from audio_generator.action import Tts
import threading
import requests
import io
import wave
import time

# フェーズ定義
PHASE_QUEUED = 0
PHASE_QUERYING = 1
PHASE_SYNTHESIZING = 2
PHASE_PLAYING = 3
PHASE_COMPLETED = 4
PHASE_CANCELED = 5
PHASE_ERROR = 6

PHASE_LABELS = {
    PHASE_QUEUED: "QUEUED",
    PHASE_QUERYING: "QUERYING",
    PHASE_SYNTHESIZING: "SYNTHESIZING",
    PHASE_PLAYING: "PLAYING",
    PHASE_COMPLETED: "COMPLETED",
    PHASE_CANCELED: "CANCELED",
    PHASE_ERROR: "ERROR"
}

class AudioGeneratorActionServer(Node):
    def __init__(self):
        super().__init__("audio_generator_action_server")
        self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
        self.declare_parameter('default_speaker_id', 3)
        self.declare_parameter('default_speed', 1.0)
        self.declare_parameter('default_pitch', 0.0)
        self.declare_parameter('default_intonation', 1.0)
        self.declare_parameter('default_volume', 1.0)

        self._action_server = ActionServer(
            self,
            Tts,
            'audio_generator',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            handle_accepted_callback=self.handle_accepted_callback
        )
        self.get_logger().info("audio_generator_action_server ready. Action: /audio_generator")

    def goal_callback(self, goal_request):
        # 受領時点の簡易バリデーション（空文字は拒否）
        if not goal_request.text.strip():
            self.get_logger().warn("Rejected goal: empty text")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info("Cancel requested.")
        return CancelResponse.ACCEPT

    def handle_accepted_callback(self, goal_handle):
        # 独自スレッドで実行
        thread = threading.Thread(target=self._execute_thread, args=(goal_handle,), daemon=True)
        thread.start()

    def publish_feedback(self, goal_handle, phase, progress, message=""):
        feedback = Tts.Feedback()
        feedback.phase = phase
        feedback.phase_label = PHASE_LABELS.get(phase, "UNKNOWN")
        feedback.progress = float(progress)
        feedback.message = message
        goal_handle.publish_feedback(feedback)

    def _execute_thread(self, goal_handle):
        result_msg = Tts.Result()
        goal = goal_handle.request

        # デフォルトパラメータ反映
        speaker_id = goal.speaker_id if goal.speaker_id >= 0 else \
            self.get_parameter('default_speaker_id').get_parameter_value().integer_value
        speed = goal.speed if goal.speed > 0 else \
            float(self.get_parameter('default_speed').get_parameter_value().double_value)
        pitch = goal.pitch if goal.pitch != 0.0 else \
            float(self.get_parameter('default_pitch').get_parameter_value().double_value)
        intonation = goal.intonation if goal.intonation > 0 else \
            float(self.get_parameter('default_intonation').get_parameter_value().double_value)
        volume = goal.volume if goal.volume > 0 else \
            float(self.get_parameter('default_volume').get_parameter_value().double_value)
        engine_url = self.get_parameter('engine_url').get_parameter_value().string_value

        text = goal.text.strip()

        def check_cancel(phase_before_next=False):
            if goal_handle.is_cancel_requested:
                self.publish_feedback(goal_handle, PHASE_CANCELED, 1.0, "Canceled by client")
                goal_handle.canceled()
                result_msg.success = False
                result_msg.error = "Canceled"
                result_msg.wav_data = []
                return True
            return False

        self.publish_feedback(goal_handle, PHASE_QUEUED, 0.0, "Goal accepted and queued")
        if check_cancel():
            return

        # QUERYING
        try:
            self.publish_feedback(goal_handle, PHASE_QUERYING, 0.05, "Posting /audio_query")
            if check_cancel():
                return
            q = requests.post(
                f"{engine_url}/audio_query",
                params={
                    "text": text,
                    "speaker": speaker_id,
                    "enable_interrogative_upspeak": True,
                    "enable_katakana_english": True
                },
                timeout=30
            )
            q.raise_for_status()
            query = q.json()
        except Exception as e:
            self.publish_feedback(goal_handle, PHASE_ERROR, 1.0, f"audio_query failed: {e}")
            goal_handle.abort()
            result_msg.success = False
            result_msg.error = f"audio_query failed: {e}"
            result_msg.wav_data = []
            return

        if check_cancel():
            return

        # パラメータ適用
        query["speedScale"] = float(speed)
        query["pitchScale"] = float(pitch)
        query["intonationScale"] = float(intonation)
        query["volumeScale"] = float(volume)

        # SYNTHESIZING
        try:
            self.publish_feedback(goal_handle, PHASE_SYNTHESIZING, 0.25, "Posting /synthesis")
            if check_cancel():
                return
            wav_resp = requests.post(
                f"{engine_url}/synthesis",
                params={"speaker": speaker_id},
                json=query,
                timeout=60
            )
            wav_resp.raise_for_status()
            wav_bytes = wav_resp.content
            # 擬似的に進捗インクリメント（分割取得できないため）
            for p in [0.40, 0.55, 0.70]:
                if check_cancel():
                    return
                self.publish_feedback(goal_handle, PHASE_SYNTHESIZING, p, "Synthesis in progress (simulated)")
                time.sleep(0.05)
            self.publish_feedback(goal_handle, PHASE_SYNTHESIZING, 0.80, "Synthesis complete")
        except Exception as e:
            self.publish_feedback(goal_handle, PHASE_ERROR, 1.0, f"synthesis failed: {e}")
            goal_handle.abort()
            result_msg.success = False
            result_msg.error = f"synthesis failed: {e}"
            result_msg.wav_data = []
            return

        if check_cancel():
            return

        # PLAYING
        if goal.play:
            self.publish_feedback(goal_handle, PHASE_PLAYING, 0.85, "Playback start")
            if not self.play_wav_bytes(wav_bytes):
                self.get_logger().warn("Playback skipped or failed (no supported backend).")
                self.publish_feedback(goal_handle, PHASE_PLAYING, 0.90, "Playback skipped or failed")
            else:
                self.publish_feedback(goal_handle, PHASE_PLAYING, 0.95, "Playback done")

        if check_cancel():
            return

        # COMPLETED
        self.publish_feedback(goal_handle, PHASE_COMPLETED, 1.0, "Completed")
        result_msg.success = True
        result_msg.error = ""
        if goal.return_wav:
            result_msg.wav_data = list(wav_bytes)
        else:
            result_msg.wav_data = []
        goal_handle.succeed()
        self.get_logger().info("TTS goal succeeded.")

    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        # simpleaudio → pyaudio の順で試す
        # simpleaudio
        try:
            import simpleaudio as sa
            import wave, io
            bio = io.BytesIO(wav_bytes)
            with wave.open(bio, 'rb') as w:
                wave_obj = sa.WaveObject.from_wave_read(w)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return True
        except Exception:
            pass

        # pyaudio
        try:
            import pyaudio
            import wave, io
            pa = pyaudio.PyAudio()
            bio = io.BytesIO(wav_bytes)
            wf = wave.open(bio, 'rb')
            stream = pa.open(format=pa.get_format_from_width(wf.getsampwidth()),
                             channels=wf.getnchannels(),
                             rate=wf.getframerate(),
                             output=True)
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            wf.close()
            pa.terminate()
            return True
        except Exception:
            pass

        return False


def main():
    rclpy.init()
    node = AudioGeneratorActionServer()
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()