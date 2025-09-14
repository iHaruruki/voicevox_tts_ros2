import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from audio_generator_interfaces.action import SpeakText

from pathlib import Path
import requests
import time
import datetime
import io
import wave
import tempfile
import platform
import shutil
import subprocess
import traceback


class SpeakTextActionServer(Node):
    def __init__(self):
        super().__init__('speak_text_action_server')

        # 基本パラメータ
        self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
        self.declare_parameter('speaker_id', 3)
        self.declare_parameter('speed', 1.0)
        self.declare_parameter('pitch', 0.0)
        self.declare_parameter('intonation', 1.0)
        self.declare_parameter('volume', 1.0)
        self.declare_parameter('enable_interrogative_upspeak', True)
        self.declare_parameter('enable_katakana_english', True)
        self.declare_parameter('playback', True)
        self.declare_parameter('save_wav', True)
        self.declare_parameter('output_directory', '/tmp/audio_generator')

        out_dir = Path(self.get_parameter('output_directory').value)
        out_dir.mkdir(parents=True, exist_ok=True)

        # シンプルメモリキャッシュ（後で LRU 化可能）
        self._cache = {}

        self._action_server = ActionServer(
            self,
            SpeakText,
            'speak_text',
            execute_callback=self.execute_cb,
            goal_callback=self.goal_cb,
            cancel_callback=self.cancel_cb
        )
        self.get_logger().info("SpeakText Action Server ready.")

    def goal_cb(self, goal_request: SpeakText.Goal):
        if not goal_request.text:
            self.get_logger().warn("空テキスト goal 拒否")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_cb(self, goal_handle):
        self.get_logger().info(f"Cancel requested for goal id={goal_handle.goal_id}")
        return CancelResponse.ACCEPT

    async def execute_cb(self, goal_handle):
        goal = goal_handle.request
        started = time.perf_counter()
        excerpt = goal.text[:40] + ("..." if len(goal.text) > 40 else "")
        self.get_logger().info(f"[ACTION] Start: '{excerpt}'")

        # 初期フィードバック
        fb = SpeakText.Feedback()
        fb.state = "synthesizing"
        fb.progress = 0.0
        fb.remaining_queue = 0
        fb.excerpt = excerpt
        goal_handle.publish_feedback(fb)

        # Goalで上書き (0や負値で既定値を使う方針)
        speaker_id = goal.speaker_id if goal.speaker_id >= 0 else int(self.get_parameter('speaker_id').value)
        playback = goal.playback if goal.playback else bool(self.get_parameter('playback').value)
        speed = goal.speed if goal.speed > 0 else float(self.get_parameter('speed').value)
        pitch = goal.pitch if goal.pitch != 0 else float(self.get_parameter('pitch').value)
        intonation = goal.intonation if goal.intonation != 0 else float(self.get_parameter('intonation').value)
        volume = goal.volume if goal.volume != 0 else float(self.get_parameter('volume').value)

        engine_url = self.get_parameter('engine_url').value
        enable_interrogative_upspeak = bool(self.get_parameter('enable_interrogative_upspeak').value)
        enable_katakana_english = bool(self.get_parameter('enable_katakana_english').value)
        save_wav = bool(self.get_parameter('save_wav').value)
        output_dir = self.get_parameter('output_directory').value

        cache_key = (
            goal.text, speaker_id, speed, pitch, intonation, volume,
            enable_interrogative_upspeak, enable_katakana_english
        )
        from_cache = False
        wav_bytes = None

        if goal.allow_cache and cache_key in self._cache:
            wav_bytes = self._cache[cache_key]
            from_cache = True
            self.get_logger().info("[ACTION] Cache hit")
        else:
            try:
                query_resp = requests.post(
                    f"{engine_url}/audio_query",
                    params={
                        "text": goal.text,
                        "speaker": speaker_id,
                        "enable_interrogative_upspeak": enable_interrogative_upspeak,
                        "enable_katakana_english": enable_katakana_english
                    },
                    timeout=30
                )
                query_resp.raise_for_status()
                query = query_resp.json()
                query["speedScale"] = float(speed)
                query["pitchScale"] = float(pitch)
                query["intonationScale"] = float(intonation)
                query["volumeScale"] = float(volume)

                wav_resp = requests.post(
                    f"{engine_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=query,
                    timeout=120
                )
                wav_resp.raise_for_status()
                wav_bytes = wav_resp.content
                if goal.allow_cache:
                    self._cache[cache_key] = wav_bytes
            except Exception as e:
                self.get_logger().error(f"Synthesis failed: {e}")
                result = SpeakText.Result()
                result.success = False
                result.error_message = str(e)
                result.saved_path = ""
                result.from_cache = False
                result.elapsed_ms = int((time.perf_counter() - started) * 1000)
                result.used_speaker_id = speaker_id
                goal_handle.abort()
                return result

        if goal_handle.is_cancel_requested:
            self.get_logger().warn("Canceled after synthesis")
            result = SpeakText.Result()
            result.success = False
            result.error_message = "canceled"
            result.saved_path = ""
            result.from_cache = from_cache
            result.elapsed_ms = int((time.perf_counter() - started) * 1000)
            result.used_speaker_id = speaker_id
            goal_handle.canceled()
            return result

        fb.state = "playing" if playback else "finalizing"
        fb.progress = 0.5 if playback else 0.9
        goal_handle.publish_feedback(fb)

        saved_path = ""
        if save_wav:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            p = Path(output_dir) / f"tts_{ts}.wav"
            p.write_bytes(wav_bytes)
            saved_path = str(p)

        if playback:
            canceled = await self._play_async(wav_bytes, goal_handle)
            if canceled:
                self.get_logger().warn("Canceled during playback")
                result = SpeakText.Result()
                result.success = False
                result.error_message = "canceled"
                result.saved_path = saved_path
                result.from_cache = from_cache
                result.elapsed_ms = int((time.perf_counter() - started) * 1000)
                result.used_speaker_id = speaker_id
                goal_handle.canceled()
                return result

        fb.state = "done"
        fb.progress = 1.0
        goal_handle.publish_feedback(fb)

        result = SpeakText.Result()
        result.success = True
        result.error_message = ""
        result.saved_path = saved_path
        result.from_cache = from_cache
        result.elapsed_ms = int((time.perf_counter() - started) * 1000)
        result.used_speaker_id = speaker_id
        goal_handle.succeed()
        self.get_logger().info(f"[ACTION] Done elapsed={result.elapsed_ms}ms cache={from_cache}")
        return result

    async def _play_async(self, wav_bytes: bytes, goal_handle):
        try:
            import simpleaudio as sa
            with io.BytesIO(wav_bytes) as bio:
                with wave.open(bio, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    sample_width = wf.getsampwidth()
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
            play_obj = sa.play_buffer(frames, channels, sample_width, rate)
            while play_obj.is_playing():
                if goal_handle.is_cancel_requested:
                    play_obj.stop()
                    return True
                await self._sleep_poll()
            return False
        except Exception as e:
            self.get_logger().warn(f"simpleaudio failed: {e} -> fallback")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            if shutil.which("ffplay"):
                subprocess.run(["ffplay", "-nodisp", "-autoexit", tmp.name], check=False)
            elif shutil.which("paplay"):
                subprocess.run(["paplay", tmp.name], check=False)
            elif shutil.which("aplay"):
                subprocess.run(["aplay", tmp.name], check=False)
            elif platform.system() == "Darwin" and shutil.which("afplay"):
                subprocess.run(["afplay", tmp.name], check=False)
            return goal_handle.is_cancel_requested

    async def _sleep_poll(self):
        end = time.time() + 0.05
        while time.time() < end:
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(0.005)


def main(args=None):
    rclpy.init(args=args)
    node = SpeakTextActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()