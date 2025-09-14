# audio_generator

ROS 2 (Humble 以降想定) で VOICEVOX エンジンを用いたテキスト音声合成 (TTS) を行うパッケージです。  
以下 2 つの API スタイルを提供します:

1. Topic: 文字列トピック (`/tts_text`) を購読して合成・保存・(任意で) 再生するノード `audio_generator_node`  
2. Action: Action インターフェース (`/speak_text`) によるゴール駆動型の TTS 要求 (`tts_action_server` ノード)
Action 版ではフィードバック (進捗 / 状態 / 抜粋) やキャッシュ利用有無、キャンセル処理などが可能です。

---

## Main Features
- VOICEVOX エンジン HTTP API を用いた音声合成
- 再生 (simpleaudio 利用、不可なら ffplay/paplay/aplay 等にフォールバック)
- WAV 保存 (ファイル名にタイムスタンプ)
- 動的パラメータ変更
- (Action) 合成状態・進捗フィードバック
- (Action) キャッシュヒット判定
- (Action) キャンセル要求対応（再生中 / 合成後）
---

## パッケージ構成
```
ros2_ws/
  src/
    audio_generator/              ← 本パッケージ
    audio_generator_interfaces/   ← Action インタフェース (別パッケージ)
```
> [!IMPORTANT]
> 別途パッケージのcloneが必要です
> [audio_generator_interfaces](https://github.com/iHaruruki/audio_generator_interfaces.git)
---

## 依存・前提

| 種別 | 内容 |
|------|------|
| ROS 2 | Humble (Foxy 以降でも概ね動作する想定) |
| 音声エンジン | VOICEVOX エンジン (HTTP API) |
| Python ランタイム | 3.10+ 推奨 |
| Python ライブラリ | `requests`, `simpleaudio`(任意), ほか標準ライブラリ |
| 外部プレイヤ (フォールバック) | `ffplay` / `paplay` / `aplay` のいずれか |

VOICEVOXの設定方法
[VOICEBOX.md](/audio_generator/VOICEVOX.md)

Python 依存:
```bash
pip3 install requests simpleaudio
```
---

## Build

```bash
$ cd ~/ros2_ws
$ colcon build --symlink-install --packages-select audio_generator_interfaces
$ colcon build --symlink-install --packages-select audio_generator
$ source install/setup.bash
```

---
起動方法が`Topic`を使用した方法と`Action`を使用した方法の2つがある

## 1. Topicを使用した起動
```bash
ros2 launch audio_generator audio_generator_launch.py
```
### テキスト送信例
```bash
ros2 topic pub /tts_text std_msgs/String "data: 'こんにちは、テストです。'"
```
### 動的パラメータ変更例
```bash
ros2 param set /audio_generator_node speaker_id 1
ros2 param set /audio_generator_node speed 1.2
ros2 param set /audio_generator_node playback false
```

## 2. Actionを使用した起動

### インタフェース確認
```bash
ros2 interface show audio_generator_interfaces/action/SpeakText
```

### サーバ起動
```bash
ros2 run audio_generator tts_action_server
```

任意パラメータ上書き:
```bash
ros2 run audio_generator tts_action_server --ros-args \
  -p engine_url:=http://127.0.0.1:50021 \
  -p speaker_id:=3 \
  -p speed:=1.05 \
  -p intonation:=1.1 \
  -p playback:=true \
  -p save_wav:=true \
  -p output_directory:=/tmp/audio_generator
```

### ゴール送信 (CLI)

```bash
ros2 action send_goal --feedback /speak_text \
  audio_generator_interfaces/action/SpeakText \
  "{text: 'Action インタフェースのテストです。', speaker_id: -1, playback: true, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
```

フィードバック例:
```
Feedback:
  state: synthesizing
  progress: 0.0
  excerpt: "Action インタフェー..."
```

結果例:
```
Result:
  success: True
  saved_path: '/tmp/audio_generator/tts_2025...wav'
  from_cache: False
  elapsed_ms: 1234
```

### キャッシュ挙動

同一パラメータ + テキストで 2 回送ると 2 回目 `from_cache: True` になる:
```bash
ros2 action send_goal /speak_text audio_generator_interfaces/action/SpeakText \
"{text: 'キャッシュテスト', speaker_id: -1, playback: false, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
```

### キャンセル (簡易)

現在 CLI に直接 goal ID を指定する簡易コマンドは無いため、キャンセルを試したい場合は Python クライアントスクリプトを利用するか、拡張実装を追加します（サンプルは後述）。

---

## Action ゴール フィールド意味

| フィールド | 型 | 説明 | 特殊値扱い |
|-----------|----|------|-----------|
| text | string | 合成対象テキスト | 空は拒否 |
| speaker_id | int32 | 話者 ID | -1 でサーバ既定値 |
| playback | bool | 再生するか | false でファイル保存のみ |
| speed | float32 | 速度 (speedScale) | 0.0 ⇒ サーバ既定値を使用 |
| pitch | float32 | ピッチ (pitchScale) | 0.0 ⇒ 既定値 |
| intonation | float32 | 抑揚 (intonationScale) | 0.0 ⇒ 既定値 |
| volume | float32 | 音量 (volumeScale) | 0.0 ⇒ 既定値 |
| allow_cache | bool | キャッシュ使用可否 | false で常に再合成 |

### Feedback

| フィールド | 説明 |
|-----------|------|
| state | synthesizing / playing / finalizing / done |
| progress | 0.0〜1.0 の概算進捗 |
| remaining_queue | 将来の並列キュー用（現状 0 固定） |
| excerpt | 冒頭抜粋 (最大 40 文字 + 省略) |

### Result

| フィールド | 説明 |
|-----------|------|
| success | 成功フラグ |
| error_message | エラー時メッセージ |
| saved_path | 保存 WAV (save_wav=true のとき) |
| from_cache | キャッシュヒットか |
| elapsed_ms | 処理時間 (ms) |
| used_speaker_id | 実際に用いた話者 ID |

---

## ノード共通パラメータ (サーバ既定)

| 名前 | 型 | 説明 | 既定値 |
|------|----|------|--------|
| engine_url | string | VOICEVOX エンジン URL | http://127.0.0.1:50021 |
| speaker_id | int | 話者 ID | 3 |
| speed | double | speedScale | 1.0 |
| pitch | double | pitchScale | 0.0 |
| intonation | double | intonationScale | 1.0 |
| volume | double | volumeScale | 1.0 |
| enable_interrogative_upspeak | bool | 疑問形語尾上げ | true |
| enable_katakana_english | bool | 英単語カタカナ化 | true |
| playback | bool | 自動再生 | true |
| save_wav (Action ノード) | bool | WAV 保存有無 | true |
| output_directory | string | WAV 保存先 | /tmp/audio_generator |

Action ゴールで 0.0（または -1 等）を渡すフィールドはサーバ既定値が使用されます。

---

## Python 簡易 Action クライアント例 (任意)

`audio_generator` パッケージ内に次のファイルを追加してエントリポイント化すると CLI 実行できます。

```python
# tts_action_client.py (例)
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from audio_generator_interfaces.action import SpeakText

class TTSClient(Node):
    def __init__(self):
        super().__init__('tts_action_client')
        self.cli = ActionClient(self, SpeakText, 'speak_text')

    def send(self, text: str):
        if not self.cli.wait_for_server(timeout_sec=5):
            self.get_logger().error("Action server not available.")
            return
        goal = SpeakText.Goal()
        goal.text = text
        goal.speaker_id = -1
        goal.playback = True
        goal.speed = 0.0
        goal.pitch = 0.0
        goal.intonation = 0.0
        goal.volume = 0.0
        goal.allow_cache = True
        fut = self.cli.send_goal_async(goal, feedback_callback=self.fb)
        fut.add_done_callback(self.accepted)

    def fb(self, fb_msg):
        f = fb_msg.feedback
        self.get_logger().info(f"[FB] {f.state} {f.progress:.2f} '{f.excerpt}'")

    def accepted(self, fut):
        gh = fut.result()
        if not gh.accepted:
            self.get_logger().warn("Goal rejected.")
            rclpy.shutdown(); return
        self.get_logger().info("Goal accepted.")
        gh.get_result_async().add_done_callback(self.done)

    def done(self, fut):
        res = fut.result().result
        self.get_logger().info(f"Result success={res.success} cache={res.from_cache} path={res.saved_path}")
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    c = TTSClient()
    c.send("アクション クライアント テストです。")
    rclpy.spin(c)

if __name__ == '__main__':
    main()
```

---

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| `tts_action_server` が見つからない | setup.py の entry_points 未反映 | 再ビルド & `source install/setup.bash` |
| `ImportError: audio_generator_interfaces` | インタフェース未ビルド / source 忘れ | interfaces パッケージを先にビルド |
| HTTP 失敗 (connection refused) | VOICEVOX 未起動 / URL 違い | エンジン起動・`engine_url` パラメータ再確認 |
| 音が鳴らない | simpleaudio 未インストール | `pip3 install simpleaudio` またはフォールバック確認 |
| キャンセル遅延 | フォールバック再生 (外部コマンド) 中 | simpleaudio 利用環境に切替 |
| キャッシュ効かない | パラメータ差分 / allow_cache=false | ゴール送信 JSON を再確認 |

---

<!-- ## Quick Start

```bash
# 1) VOICEVOX 起動
docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest

# 2) ビルド
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash

# 3) Action サーバ起動
ros2 run audio_generator tts_action_server

# 4) ゴール送信 (別ターミナル)
source ~/ros2_ws/install/setup.bash
ros2 action send_goal --feedback /speak_text audio_generator_interfaces/action/SpeakText \
"{text: 'テスト', speaker_id: -1, playback: true, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
``` -->