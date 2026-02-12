import rclpy
import os
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray  # ByteMultiArray -> UInt8MultiArray
from rcl_interfaces.msg import SetParametersResult

import requests
from pathlib import Path
import platform
import shutil
import subprocess
import threading
import datetime
import traceback
import io
import wave
import tempfile
import re
from queue import Queue, Empty

class AudioGeneratorNode(Node):
    def __init__(self):
        super().__init__('voicevox_tts_topic_node')

        # Parameters
        self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
        self.declare_parameter('speaker_id', 3)
        self.declare_parameter('speed', 1.0)
        self.declare_parameter('pitch', 0.0)
        self.declare_parameter('intonation', 1.0)
        self.declare_parameter('volume', 1.0)
        self.declare_parameter('enable_interrogative_upspeak', True)
        self.declare_parameter('enable_katakana_english', True)
        self.declare_parameter('playback', True)
        self.declare_parameter('output_directory', os.path.expanduser('/$HOME/ros2_ws/src/voicevox_tts_ros2'))
        self.declare_parameter('save_wav', False)
        self.declare_parameter('publish_audio_bytes', False)
        self.declare_parameter('stream_sentence_mode', True)
        self.declare_parameter('sentence_separators', '。！？!?\\n')

        # Subscriber
        self.subscription = self.create_subscription(
            String,
            '/voicevox_tts_text',
            self.text_callback,
            10
        )

        # Publisher: /tts_audio (各 WAV セグメントの生バイト列)
        self.audio_pub = self.create_publisher(UInt8MultiArray, '/tts_audio', 10)

        # Locks / state
        self._synthesis_lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._stream_active = False
        self._stream_queue: Queue[str] = Queue()
        self._cancel_stream = False

        out_dir = Path(self.get_parameter('output_directory').value)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f"Audio output directory: {out_dir}")

        self.add_on_set_parameters_callback(self.on_param_change)

    # --------------- Parameter callback ---------------
    def on_param_change(self, params):
        for p in params:
            name, val = p.name, p.value
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

    # --------------- Topic callback ---------------
    def text_callback(self, msg: String):
        text = msg.data.strip()
        if not text:
            self.get_logger().warn("空文字列を受信したため無視します。")
            return
        if self.get_parameter('stream_sentence_mode').value:
            self._enqueue_stream_text(text)
        else:
            threading.Thread(target=self._handle_tts_single, args=(text,), daemon=True).start()

    # --------------- Streaming sentence mode ---------------
    def _enqueue_stream_text(self, full_text: str):
        sentences = self._split_sentences(full_text, self.get_parameter('sentence_separators').value)
        if not sentences:
            return
        with self._stream_lock:
            for s in sentences:
                self._stream_queue.put(s)
            if not self._stream_active:
                self._stream_active = True
                self._cancel_stream = False
                threading.Thread(target=self._stream_worker, daemon=True).start()
                self.get_logger().info(f"ストリーム開始: {len(sentences)} 文をキューへ")
            else:
                self.get_logger().info(f"ストリームに {len(sentences)} 文を追加 (残キュー: {self._stream_queue.qsize()})")

    def _split_sentences(self, text: str, seps: str):
        if not text:
            return []
        pattern = f"([{re.escape(seps)}])"
        parts = re.split(pattern, text)
        merged = []
        buf = ""
        for p in parts:
            if not p:
                continue
            if len(p) == 1 and p in seps:
                buf += p
                merged.append(buf.strip())
                buf = ""
            else:
                buf += p
        if buf.strip():
            merged.append(buf.strip())
        return [m for m in merged if m]

    def _stream_worker(self):
        self.get_logger().info("ストリームワーカー起動")
        try:
            while not self._cancel_stream:
                try:
                    sentence = self._stream_queue.get(timeout=0.3)
                except Empty:
                    if self._stream_queue.empty():
                        if not self._wait_for_more(1.0):
                            self.get_logger().info("ストリーム完了（追加文なし）")
                            break
                        else:
                            continue
                    continue

                params = self._collect_params()
                short = sentence[:30] + ('...' if len(sentence) > 30 else '')
                self.get_logger().info(f"[STREAM] 合成: '{short}'")
                try:
                    wav_bytes, saved_path = self._tts_bytes(sentence, **params)
                    if saved_path:
                        self.get_logger().info(f"[STREAM] 保存: {saved_path.name}")
                    if params['publish_audio_bytes']:
                        msg = UInt8MultiArray()
                        msg.data = list(wav_bytes)  # uint8[] に int リストをそのまま
                        self.audio_pub.publish(msg)
                        self.get_logger().info(f"[STREAM] publish {len(wav_bytes)} bytes")
                    if params['playback']:
                        self._play_wav_bytes(wav_bytes)
                except Exception as e:
                    self.get_logger().error(f"[STREAM] 合成失敗: {e}")
                finally:
                    self._stream_queue.task_done()
        finally:
            with self._stream_lock:
                self._stream_active = False
            self.get_logger().info("ストリームワーカー終了")

    def _wait_for_more(self, seconds: float):
        import time
        end = time.time() + seconds
        while time.time() < end:
            if not self._stream_queue.empty():
                return True
            time.sleep(0.1)
        return False

    def cancel_stream(self):
        with self._stream_lock:
            self._cancel_stream = True
        while not self._stream_queue.empty():
            try:
                self._stream_queue.get_nowait()
                self._stream_queue.task_done()
            except Empty:
                break
        self.get_logger().info("ストリームキャンセル指示")

    # --------------- Single mode ---------------
    def _handle_tts_single(self, text: str):
        if not self._synthesis_lock.acquire(blocking=False):
            self.get_logger().warn("前の音声合成中のためスキップ: " + text)
            return
        try:
            params = self._collect_params()
            short = text[:40] + ('...' if len(text) > 40 else '')
            self.get_logger().info(f"合成開始: speaker={params['speaker_id']} text='{short}'")
            wav_bytes, saved_path = self._tts_bytes(text, **params)
            if saved_path:
                self.get_logger().info(f"合成完了 (保存): {saved_path}")
            else:
                self.get_logger().info("合成完了 (メモリのみ)")
            if params['publish_audio_bytes']:
                msg = UInt8MultiArray()
                msg.data = list(wav_bytes)
                self.audio_pub.publish(msg)
                self.get_logger().info(f"/tts_audio に {len(wav_bytes)} bytes publish")
            if params['playback']:
                self._play_wav_bytes(wav_bytes)
        except Exception as e:
            self.get_logger().error(f"合成失敗: {e}\n{traceback.format_exc()}")
        finally:
            self._synthesis_lock.release()

    # --------------- Common helpers ---------------
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
            'save_wav': bool(self.get_parameter('save_wav').value),
            'publish_audio_bytes': bool(self.get_parameter('publish_audio_bytes').value),
        }

    def _tts_bytes(self, text: str, engine_url: str, speaker_id: int, speed: float,
                   pitch: float, intonation: float, volume: float,
                   enable_interrogative_upspeak: bool, enable_katakana_english: bool,
                   output_directory: str, save_wav: bool, **kwargs):
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
            timeout=120
        )
        synth_resp.raise_for_status()
        wav_bytes = synth_resp.content

        saved_path = None
        if save_wav:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = Path(output_directory) / f"tts_{ts}.wav"
            path.write_bytes(wav_bytes)
            saved_path = path
        return wav_bytes, saved_path

    def _play_wav_bytes(self, wav_bytes: bytes):
        try:
            import simpleaudio as sa
            with io.BytesIO(wav_bytes) as bio:
                with wave.open(bio, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    sample_width = wf.getsampwidth()
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
            play_obj = sa.play_buffer(frames, channels, sample_width, rate)
            play_obj.wait_done()
            self.get_logger().info("再生完了(simpleaudio)")
            return
        except Exception as e:
            self.get_logger().warn(f"simpleaudio再生失敗: {e} -> フォールバック")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            path = tmp.name
            if shutil.which("ffplay"):
                subprocess.run(["ffplay", "-nodisp", "-autoexit", path], check=False); return
            if shutil.which("paplay"):
                subprocess.run(["paplay", path], check=False); return
            if shutil.which("aplay"):
                subprocess.run(["aplay", path], check=False); return
            if platform.system() == "Darwin" and shutil.which("afplay"):
                subprocess.run(["afplay", path], check=False); return
            if platform.system() == "Windows":
                ps = f"(New-Object Media.SoundPlayer '{path}').PlaySync()"
                subprocess.run(["powershell", "-c", ps], check=False); return
            self.get_logger().error("再生手段が見つかりません。")

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