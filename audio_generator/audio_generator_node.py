import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from rcl_interfaces.msg import SetParametersResult  # 修正: ここからインポート

import requests
from pathlib import Path
import platform
import shutil
import subprocess
import threading
import datetime
import traceback


class AudioGeneratorNode(Node):
    def __init__(self):
        super().__init__('audio_generator_node')

        # Declare parameters
        self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
        self.declare_parameter('speaker_id', 3)
        self.declare_parameter('speed', 1.0)
        self.declare_parameter('pitch', 0.0)
        self.declare_parameter('intonation', 1.0)
        self.declare_parameter('volume', 1.0)
        self.declare_parameter('enable_interrogative_upspeak', True)
        self.declare_parameter('enable_katakana_english', True)
        self.declare_parameter('playback', True)
        self.declare_parameter('output_directory', '/tmp/audio_generator')

        # Subscription
        self.subscription = self.create_subscription(
            String,
            '/tts_text',
            self.text_callback,
            10
        )

        self._synthesis_lock = threading.Lock()

        out_dir = Path(self.get_parameter('output_directory').value)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f"Audio output directory: {out_dir}")

        self.add_on_set_parameters_callback(self.on_param_change)

    def on_param_change(self, params):
        """
        パラメータ動的変更コールバック。
        無効な値が来た場合は失敗を返して却下する。
        """
        for p in params:
            name = p.name
            val = p.value
            # 簡易バリデーション
            if name == 'speed' and (val <= 0 or val > 5.0):
                return SetParametersResult(successful=False, reason="speed must be in (0, 5.0]")
            if name == 'volume' and (val <= 0 or val > 5.0):
                return SetParametersResult(successful=False, reason="volume must be in (0, 5.0]")
            if name == 'intonation' and (val < 0 or val > 5.0):
                return SetParametersResult(successful=False, reason="intonation must be in [0, 5.0]")
            if name == 'pitch' and (val < -5.0 or val > 5.0):
                return SetParametersResult(successful=False, reason="pitch must be in [-5.0, 5.0]")
            if name == 'speaker_id' and (val < 0):
                return SetParametersResult(successful=False, reason="speaker_id must be >= 0")
            if name == 'output_directory':
                try:
                    Path(val).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return SetParametersResult(successful=False, reason=f"Cannot create output_directory: {e}")

            self.get_logger().info(f"Parameter changed: {name} -> {val}")

        return SetParametersResult(successful=True)

    def text_callback(self, msg: String):
        text = msg.data.strip()
        if not text:
            self.get_logger().warn("空文字列を受信したため無視します。")
            return
        threading.Thread(target=self._handle_tts, args=(text,), daemon=True).start()

    def _handle_tts(self, text: str):
        if not self._synthesis_lock.acquire(blocking=False):
            self.get_logger().warn("前の音声合成中のためスキップ: " + text)
            return
        try:
            params = self._collect_params()
            self.get_logger().info(
                f"合成開始: speaker={params['speaker_id']} text='{text[:40] + ('...' if len(text) > 40 else '')}'")
            wav_path = self._tts(
                text=text,
                **params
            )
            self.get_logger().info(f"合成完了: {wav_path}")
            if params['playback']:
                self._play_wav(wav_path)
        except Exception as e:
            self.get_logger().error(f"合成失敗: {e}\n{traceback.format_exc()}")
        finally:
            self._synthesis_lock.release()

    def _collect_params(self):
        return {
            'engine_url': self.get_parameter('engine_url').value,
            'speaker_id': int(self.get_parameter('speaker_id').value),
            'speed': float(self.get_parameter('speed').value),
            'pitch': float(self.get_parameter('pitch').value),
            'intonation': float(self.get_parameter('intonation').value),
            'volume': float(self.get_parameter('volume').value),
            'enable_interrogative_upspeak': bool(self.get_parameter('enable_interrogative_upspeak').value),
            'enable_katakana_english': bool(self.get_parameter('enable_katakana_english').value),
            'playback': bool(self.get_parameter('playback').value),
            'output_directory': self.get_parameter('output_directory').value,
        }

    def _tts(self,
             text: str,
             engine_url: str,
             speaker_id: int,
             speed: float,
             pitch: float,
             intonation: float,
             volume: float,
             enable_interrogative_upspeak: bool,
             enable_katakana_english: bool,
             output_directory: str,
             **kwargs):
        query_resp = requests.post(
            f"{engine_url}/audio_query",
            params={
                "text": text,
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

        synth_resp = requests.post(
            f"{engine_url}/synthesis",
            params={"speaker": speaker_id},
            json=query,
            timeout=60
        )
        synth_resp.raise_for_status()

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = Path(output_directory) / f"tts_{ts}.wav"
        path.write_bytes(synth_resp.content)
        return path

    def _play_wav(self, path: Path):
        try:
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(str(path))
            play_obj = wave_obj.play()
            play_obj.wait_done()
            self.get_logger().info("再生完了(simpleaudio)")
            return
        except Exception as e:
            self.get_logger().warn(f"simpleaudio再生失敗: {e} -> フォールバック")

        if shutil.which("ffplay"):
            subprocess.run(["ffplay", "-nodisp", "-autoexit", str(path)], check=False)
            return
        if shutil.which("paplay"):
            subprocess.run(["paplay", str(path)], check=False)
            return
        if shutil.which("aplay"):
            subprocess.run(["aplay", str(path)], check=False)
            return
        if platform.system() == "Darwin" and shutil.which("afplay"):
            subprocess.run(["afplay", str(path)], check=False)
            return
        if platform.system() == "Windows":
            ps = f"(New-Object Media.SoundPlayer '{path}').PlaySync()"
            subprocess.run(["powershell", "-c", ps], check=False)
            return
        self.get_logger().error("再生手段が見つかりません。手動で WAV を再生してください: " + str(path))


def main(args=None):
    rclpy.init(args=args)
    node = AudioGeneratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info("Shutting down.")
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()