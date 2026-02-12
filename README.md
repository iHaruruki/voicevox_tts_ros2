# voicevox_tts_ros2

ROS 2 (Humble 以降想定) で VOICEVOX エンジンを用いたテキスト音声合成 (TTS) を行うパッケージです。  
以下 2 つの API スタイルを提供します:

1. [Topic](#1-topicを使用した起動): 文字列トピック (`/voicevox_tts_text`) を購読して合成・保存・(任意で) 再生するノード  
2. [Action](#2-actionを使用した起動): Action インターフェース (`/speak_text`) によるゴール駆動型の TTS 要求 (`SpeakTextActionServer` ノード)

> [!TIP]
> Action 版ではフィードバック (進捗 / 状態 / 抜粋) やキャッシュ利用有無、キャンセル処理などが可能です。

---

> [!NOTE]
> 本プログラムは [VOICEVOX](https://voicevox.hiroshiba.jp/) のエンジンを利用して音声合成を行います。  
> 生成される音声（例: 四国めたん / ずんだもん 等）を利用・公開する際は、各キャラクターの利用規約・ガイドラインに従ってください。  
> VOICEVOX 音声モデル 利用規約: [VOICEVOX ソフトウェア利用規約](https://voicevox.hiroshiba.jp/term/)  
> デフォルト設定ではずんだもんを利用（VOICEVOX:ずんだもん）

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

## Package Configuration

```text
ros2_ws/
  src/
    voicevox_tts_ros2/              ← 本パッケージ
    voicevox_tts_interface_ros2/    ← Action インタフェース (別パッケージ)
```

> [!IMPORTANT]
> 別途パッケージ ([voicevox_tts_interface_ros2](https://github.com/iHaruruki/voicevox_tts_interface_ros2.git)) の clone が必要です。  
> [Setup](#setup) を参照してください。

---

## Dependencies

| 種別 | 内容 |
|------|------|
| ROS 2 | Humble |
| 音声エンジン | VOICEVOX エンジン (HTTP API) |
| Python ランタイム | 3.10+ 推奨 |
| Python ライブラリ | `requests`, `simpleaudio` (任意), ほか標準ライブラリ |
| 外部プレイヤ (フォールバック) | `ffplay` / `paplay` / `aplay` のいずれか |

---

## Setup

1. **Install VOICEVOX**  
   手順は以下を参照してください。  
   [VOICEVOX.md](VOICEVOX.md)

2. **Python 依存ライブラリインストール**

   ```bash
   pip3 install requests simpleaudio
   ```

3. **本パッケージの clone**

   ```bash
   cd ~/ros2_ws/src
   git clone https://github.com/iHaruruki/voicevox_tts_ros2.git
   ```

4. **`voicevox_tts_interface_ros2` パッケージの clone**

   ```bash
   cd ~/ros2_ws/src
   git clone https://github.com/iHaruruki/voicevox_tts_interface_ros2.git
   ```

5. **ビルド**

   ```bash
   cd ~/ros2_ws
   colcon build --symlink-install --packages-select voicevox_tts_interface_ros2
   source install/setup.bash
   colcon build --symlink-install --packages-select voicevox_tts_ros2
   source install/setup.bash
   ```

---

## How to Use

起動方法が [Topic](#1-topicを使用した起動) を使用した方法と [Action](#2-actionを使用した起動) を使用した方法の 2 つあります。

---

### 1. Topicを使用した起動

1. **VOICEVOX の起動**

   ```bash
   ./.voicevox/VOICEVOX.AppImage
   ```

2. **ノード起動**

   ```bash
   ros2 launch voicevox_tts_ros2 audio_generator_launch.py
   ```

3. **コマンドラインからテキスト送信**

   ```bash
   ros2 topic pub --once /voicevox_tts_text std_msgs/msg/String "data: 'こんにちは、テストです。'"
   ```

4. **`.txt` ファイルからテキスト送信**

   `speech1.txt` ファイルを作成:

   ```bash
   nano ~/ros2_ws/src/voicevox_tts_ros2/speech_script/speech1.txt
   ```

   ```text
   これは音声読み上げのテスト用サンプル文章です。およそ三百文字程度になるように、適度な長さの文をいくつか並べています。
   句読点や疑問文、感嘆符などが含まれていることで、イントネーションやポーズの違いも確認しやすくなります。
   例えば、こうした説明文を読み上げることで、話速や声の高さ、抑揚の強さなどを調整しやすくなります。
   もし途中で不自然な区切れ方をしてしまう場合は、読点を増やしたり、改行を入れたりして文の区切り方を調整してみてください。
   ```

   ```bash
   chmod +x ~/ros2_ws/src/voicevox_tts_ros2/voicevox_tts_ros2/topic_pub.py
   python3 ~/ros2_ws/src/voicevox_tts_ros2/voicevox_tts_ros2/topic_pub.py
   ```

#### Topic ノードの動的パラメータ

実装例（`audio_generator_node` 側）のパラメータ宣言:

```python
self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
self.declare_parameter('speaker_id', 3)
self.declare_parameter('speed', 1.0)
self.declare_parameter('pitch', 0.0)
self.declare_parameter('intonation', 1.0)
self.declare_parameter('volume', 1.0)
self.declare_parameter('enable_interrogative_upspeak', True)
self.declare_parameter('enable_katakana_english', True)
self.declare_parameter('playback', True)
self.declare_parameter('output_directory', os.path.expanduser('~/ros2_ws/src/voicevox_tts_ros2'))
self.declare_parameter('save_wav', False)
self.declare_parameter('publish_audio_bytes', True)
self.declare_parameter('stream_sentence_mode', True)
self.declare_parameter('sentence_separators', '。！？!?\n')
```

| パラメータ | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| engine_url | string | http://127.0.0.1:50021 | VOICEVOX エンジン URL |
| speaker_id | int | 3 | 話者 ID ([詳細](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md)) |
| speed | double | 1.0 | speedScale |
| pitch | double | 0.0 | pitchScale |
| intonation | double | 1.0 | intonationScale |
| volume | double | 1.0 | volumeScale |
| enable_interrogative_upspeak | bool | true | 疑問形語尾上げ |
| enable_katakana_english | bool | true | 英単語カタカナ化 |
| playback | bool | true | 自動再生有無 |
| output_directory | string | `~/ros2_ws/src/voicevox_tts_ros2` | WAV 保存先 |
| save_wav | bool | false | false で保存抑止 (再生のみ) |
| publish_audio_bytes | bool | true | 合成した音声データ（WAV バイト列）を `/tts_audio` トピックに配信するかどうか |
| stream_sentence_mode | bool | true | true の場合、受信したテキストを文ごとに分割して順次合成するストリームモードを有効化 |
| sentence_separators | string | `。！？!?\n` | ストリームモードで文の区切りとして扱う文字の集合 |

**パラメータ変更例**

```bash
ros2 param set /tts_topic_node speaker_id 1
ros2 param set /tts_topic_node speed 1.2
ros2 param set /tts_topic_node playback false
```

---

### 2. Actionを使用した起動

#### インタフェース確認

```bash
ros2 interface show voicevox_tts_interface_ros2/action/SpeakText
```

表示内容:

```text
# Goal
string text
int32 speaker_id
bool playback
float32 speed
float32 pitch
float32 intonation
float32 volume
bool allow_cache
---
# Result
bool success
string error_message
string saved_path
bool from_cache
int32 elapsed_ms
int32 used_speaker_id
---
# Feedback
string state
float32 progress
int32 remaining_queue
string excerpt
```

#### サーバ起動

1. **VOICEVOX 起動**

   ```bash
   ./.voicevox/VOICEVOX.AppImage
   ```

2. **Action サーバノード起動**

   ```bash
   ros2 run voicevox_tts_ros2 tts_action_server_node
   ```

`tts_action_server_node` が起動する `SpeakTextActionServer` のパラメータ宣言は以下の通りです（Topic 側と揃えています）:

```python
self.declare_parameter('engine_url', 'http://127.0.0.1:50021')
self.declare_parameter('speaker_id', 3)
self.declare_parameter('speed', 1.0)
self.declare_parameter('pitch', 0.0)
self.declare_parameter('intonation', 1.0)
self.declare_parameter('volume', 1.0)
self.declare_parameter('enable_interrogative_upspeak', True)
self.declare_parameter('enable_katakana_english', True)
self.declare_parameter('playback', True)
self.declare_parameter('output_directory', os.path.expanduser('~/ros2_ws/src/voicevox_tts_ros2'))
self.declare_parameter('save_wav', False)
self.declare_parameter('publish_audio_bytes', True)
self.declare_parameter('stream_sentence_mode', True)
self.declare_parameter('sentence_separators', '。！？!?\n')
```

任意パラメータ上書き例:

```bash
ros2 run voicevox_tts_ros2 tts_action_server_node --ros-args \
  -p engine_url:=http://127.0.0.1:50021 \
  -p speaker_id:=3 \
  -p speed:=0.85 \
  -p pitch:=0.0 \
  -p intonation:=1.1 \
  -p volume:=1.0 \
  -p enable_interrogative_upspeak:=true \
  -p enable_katakana_english:=true \
  -p playback:=true \
  -p output_directory:=/tmp/audio_generator \
  -p save_wav:=true \
  -p publish_audio_bytes:=true \
  -p stream_sentence_mode:=true \
  -p sentence_separators:='。！？!?\n'
```

#### ゴール送信 (CLI)

```bash
ros2 action send_goal --feedback /speak_text \
  voicevox_tts_interface_ros2/action/SpeakText \
  "{text: 'Action インタフェースのテストです。', speaker_id: -1, playback: true, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
```

**フィードバック例**

```text
Feedback:
  state: synthesizing
  progress: 0.0
  remaining_queue: 0
  excerpt: "Action インタフェー..."
```

**結果例**

```text
Result:
  success: True
  error_message: ''
  saved_path: '/tmp/audio_generator/tts_2025...wav'
  from_cache: False
  elapsed_ms: 1234
  used_speaker_id: 3
```

#### キャッシュ挙動

同一パラメータ + テキストで 2 回送ると 2 回目 `from_cache: True` になります:

```bash
ros2 action send_goal --feedback /speak_text \
  voicevox_tts_interface_ros2/action/SpeakText \
  "{text: 'キャッシュテスト', speaker_id: -1, playback: false, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
```

---

#### 動的パラメータ (Action サーバ)

**Action サーバ (`SpeakTextActionServer`)**

| パラメータ | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| engine_url | string | http://127.0.0.1:50021 | VOICEVOX エンジン URL |
| speaker_id | int | 3 | 既定話者 (ゴールで -1 指定時に使用) ([詳細](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md)) |
| speed | double | 1.0 | 既定 speedScale |
| pitch | double | 0.0 | 既定 pitchScale |
| intonation | double | 1.0 | 既定 intonationScale |
| volume | double | 1.0 | 既定 volumeScale |
| enable_interrogative_upspeak | bool | true | 疑問形語尾上げ |
| enable_katakana_english | bool | true | 英単語カタカナ化 |
| playback | bool | true | ゴール未指定なら使用 |
| output_directory | string | `~/ros2_ws/src/voicevox_tts_ros2` | WAV 保存先 |
| save_wav | bool | false | false で保存抑止 (再生のみ) |
| publish_audio_bytes | bool | true | 将来拡張用: ���成した音声データ（WAV バイト列）をトピック配信するかどうか |
| stream_sentence_mode | bool | true | 将来拡張用: true の場合、受信テキストを文ごとに分割して順次合成するストリームモードを有効化 |
| sentence_separators | string | `。！？!?\n` | 将来拡張用: ストリームモードで文の区切りとして扱う文字の集合 |

Action サーバは Topic 版と同様の音声パラメータ (`speed`, `pitch`, `intonation`, `volume`, `enable_*` など) をサーバ側パラメータとして持ち、  
ゴールフィールドで 0 や負値が来た場合にはこれらの既定パラメータを使用する実装になっています。

**Action ゴール (`SpeakText.Goal`)**

| フィールド | 型 | 特殊値 / 既定解釈 | 説明 |
|-----------|----|-------------------|------|
| text | string | 空 → 拒否 | 合成対象文字列 |
| speaker_id | int32 | -1 → サーバ既定 | 0 以上で強制上書き |
| playback | bool | なし | 合成後再生するか |
| speed | float32 | 0.0 → サーバ既定 | >0 で上書き |
| pitch | float32 | 0.0 → 既定 | != 0.0 で上書き |
| intonation | float32 | 0.0 → 既定 | != 0.0 で上書き |
| volume | float32 | 0.0 → 既定 | != 0.0 で上書き |
| allow_cache | bool | false → キャッシュ不使用 | true でキャッシュ利用 / 保存 |

**Action Feedback**

| フィールド | 説明 |
|-----------|------|
| state | `synthesizing` / `playing` / `finalizing` / `done` |
| progress | 0.0〜1.0 概算 |
| remaining_queue | 将来拡張用 (現状 0) |
| excerpt | テキスト冒頭抜粋 (最大 40 文字) |

**Action Result**

| フィールド | 説明 |
|-----------|------|
| success | 成功フラグ |
| error_message | エラー時メッセージ |
| saved_path | 保存ファイル (`save_wav=true` のときのみ) |
| from_cache | キャッシュヒットか |
| elapsed_ms | 経過ミリ秒 |
| used_speaker_id | 実際に用いた話者 ID |

---

## Python 簡易 Action クライアント例

[`tts_action_client.py`](voicevox_tts_ros2/tts_action_client.py)

```text
ros2_ws/
  src/
    voicevox_tts_ros2/
      voicevox_tts_ros2/
        tts_action_client.py
```

ノード起動:

```bash
ros2 run voicevox_tts_ros2 tts_action_client
```

---

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| `tts_action_server_node` が見つからない | `setup.py` の `entry_points` 未反映 | 再ビルド & `source install/setup.bash` |
| `ImportError: voicevox_tts_interface_ros2` | インタフェース未ビルド / `source` 忘れ | interface パッケージを先にビルドし、`source` を実行 |
| HTTP 失敗 (connection refused) | VOICEVOX 未起動 / URL 違い | エンジン起動・`engine_url` パラメータ再確認 |
| 音が鳴らない | `simpleaudio` 未インストール | `pip3 install simpleaudio` またはフォールバック確認 |
| キャンセル遅延 | フォールバック再生 (外部コマンド) 中 | `simpleaudio` 利用環境に切替 |
| キャッシュ効かない | パラメータ差分 / `allow_cache=false` | ゴール送信 JSON を再確認 |

---