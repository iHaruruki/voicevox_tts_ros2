# audio_generator

ROS 2 (Humble 以降想定) で VOICEVOX エンジンを用いたテキスト音声合成 (TTS) を行うパッケージです.<br>
以下 2 つの API スタイルを提供します:

1. [Topic](#1-topicを使用した起動): 文字列トピック (`/tts_text`) を購読して合成・保存・(任意で) 再生するノード `audio_generator_node`  
2. [Action](#2-actionを使用した起動): Action インターフェース (`/speak_text`) によるゴール駆動型の TTS 要求 (`tts_action_server` ノード)
> [!TIP]
> Action 版ではフィードバック (進捗 / 状態 / 抜粋) やキャッシュ利用有無、キャンセル処理などが可能です.
---
> [!NOTE]
> 本プログラムは [VOICEVOX](https://voicevox.hiroshiba.jp/) のエンジンを利用して音声合成を行います.    
> 生成される音声（例: 四国めたん / ずんだもん 等）を利用・公開する際は、各キャラクターの利用規約・ガイドラインに従ってください.<br>
> VOICEVOX 音声モデル 利用規約: [VOICEVOX ソフトウェア利用規約](https://voicevox.hiroshiba.jp/term/) <br>
> デフォルト設定ではずんだもんを利用（VOICEVOX:ずんだもん）

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
```
ros2_ws/
  src/
    audio_generator/              ← 本パッケージ
    audio_generator_interfaces/   ← Action インタフェース (別パッケージ)
```
> [!IMPORTANT]
> 別途パッケージ([audio_generator_interfaces](https://github.com/iHaruruki/audio_generator_interfaces.git))のcloneが必要です.<br>
> [setup](#setup)を参照
---

## Dependencies

| 種別 | 内容 |
|------|------|
| ROS 2 | Humble |
| 音声エンジン | VOICEVOX エンジン (HTTP API) |
| Python ランタイム | 3.10+ 推奨 |
| Python ライブラリ | `requests`, `simpleaudio`(任意), ほか標準ライブラリ |
| 外部プレイヤ (フォールバック) | `ffplay` / `paplay` / `aplay` のいずれか |
---

## Setup
1. Install VOICEVOX
Please follow link<br>
[VOICEBOX.md](https://github.com/iHaruruki/audio_generator/blob/feature/VOICEVOX.md)
2. Python 依存:
```bash
pip3 install requests simpleaudio
```
3. Clone this package
```bash
cd ~/ros2_ws/src
git clone https://github.com/iHaruruki/audio_generator.git
```
4. Clone `audio_generator_interfaces` package
```bash
cd ~/ros2_ws/src
git clone https://github.com/iHaruruki/audio_generator_interfaces.git
```
5. Build
```bash
$ cd ~/ros2_ws
$ colcon build --symlink-install --packages-select audio_generator_interfaces
$ colcon build --symlink-install --packages-select audio_generator
$ source install/setup.bash
```
---

## How to Use
起動方法が[Topic](#1-topicを使用した起動)を使用した方法と[Action](#2-actionを使用した起動)を使用した方法の2つがある.

### 1. Topicを使用した起動
Launch VOICEVOX
```bash
./.voicevox/VOICEVOX.AppImage
```
Run node
```bash
ros2 launch audio_generator audio_generator_launch.py
```
Send text
```bash
ros2 topic pub /tts_text std_msgs/String "data: 'こんにちは、テストです。'"
```
#### 動的パラメータ
| パラメータ | 型 | 既定値 | 説明 |
|------------|----|--------|------|
| engine_url | string | http://127.0.0.1:50021 | VOICEVOX エンジン URL |
| speaker_id | int | 3 | 話者 ID ([詳細](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md))|
| speed | double | 1.0 | speedScale |
| pitch | double | 0.0 | pitchScale |
| intonation | double | 1.0 | intonationScale |
| volume | double | 1.0 | volumeScale |
| enable_interrogative_upspeak | bool | true | 疑問形語尾上げ |
| enable_katakana_english | bool | true | 英単語カタカナ化 |
| playback | bool | true | 自動再生有無 |
| output_directory | string | /tmp/audio_generator | WAV 保存先 |

**パラメータ変更例**
```bash
ros2 param set /audio_generator_node speaker_id 1
ros2 param set /audio_generator_node speed 1.2
ros2 param set /audio_generator_node playback false
```

### 2. Actionを使用した起動
#### インタフェース確認
```bash
ros2 interface show audio_generator_interfaces/action/SpeakText
```
Display
```bash
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
Launch VOICEVOX
```bash
./.voicevox/VOICEVOX.AppImage
```
Run node
```bash
ros2 run audio_generator tts_action_server
```

任意パラメータ上書き:
```bash
ros2 run audio_generator tts_action_server --ros-args \
  -p engine_url:=http://127.0.0.1:50021 \
  -p speaker_id:=3 \
  -p speed:=0.85 \
  -p intonation:=1.1 \
  -p playback:=true \
  -p save_wav:=false \
  -p output_directory:=/tmp/audio_generator
```

#### ゴール送信 (CLI)
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

#### キャッシュ挙動
同一パラメータ + テキストで 2 回送ると 2 回目 `from_cache: True` になる:
```bash
ros2 action send_goal /speak_text audio_generator_interfaces/action/SpeakText \
"{text: 'キャッシュテスト', speaker_id: -1, playback: false, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
```
#### 動的パラメータ

**Action サーバ (`tts_action_server`)**
| パラメータ | 型 | 既定値 | 説明 |
|------------|----|--------|------|
| engine_url | string | http://127.0.0.1:50021 | VOICEVOX エンジン URL |
| speaker_id | int | 3 | 既定話者 (ゴールで -1 指定時に使用) ([詳細](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md))|
| speed | double | 1.0 | 既定 speedScale |
| pitch | double | 0.0 | 既定 pitchScale |
| intonation | double | 1.0 | 既定 intonationScale |
| volume | double | 1.0 | 既定 volumeScale |
| enable_interrogative_upspeak | bool | true | 疑問形語尾上げ |
| enable_katakana_english | bool | true | 英単語カタカナ化 |
| playback | bool | true | ゴール未指定なら使用 |
| save_wav | bool | true | false で保存抑止 (再生のみ) |
| output_directory | string | /tmp/audio_generator | WAV 保存先 |

**Action ゴール (SpeakText.Goal)**
| フィールド | 型 | 特殊値 / 既定解釈 | 説明 |
|-----------|----|-------------------|------|
| text | string | 空→拒否 | 合成対象文字列 |
| speaker_id | int32 | -1→サーバ既定 | 0 以上で強制上書き |
| playback | bool | なし | 合成後再生するか |
| speed | float32 | 0.0→サーバ既定 | >0 で上書き |
| pitch | float32 | 0.0→既定 | !=0.0 で上書き |
| intonation | float32 | 0.0→既定 | !=0.0 で上書き |
| volume | float32 | 0.0→既定 | !=0.0 で上書き |
| allow_cache | bool | false→キャッシュ不使用 | true でキャッシュ利用/保存 |

**Action Feedback**
| フィールド | 説明 |
|-----------|------|
| state | synthesizing / playing / finalizing / done |
| progress | 0.0〜1.0 概算 |
| remaining_queue | 将来拡張用 (現状 0) |
| excerpt | テキスト冒頭抜粋 (最大 40 文字) |

**Action Result**
| フィールド | 説明 |
|-----------|------|
| success | 成功フラグ |
| error_message | エラー時メッセージ |
| saved_path | 保存ファイル（`save_wav=true`） |
| from_cache | キャッシュヒットか |
| elapsed_ms | 経過ミリ秒 |
| used_speaker_id | 実際に用いた話者 ID |
---

### Python 簡易 Action クライアント例
[tts_action_client.py](/audio_generator/tts_action_client.py)
```
ros2_ws/
  src/
    audio_generator/
      audio_generator/
        tts_action_client.py
```
Node about `tts_action_client.py`
```shell
ros2 run audio_generator tts_action_client
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
# 1. VOICEVOX 起動


# 2. ビルド & セットアップ
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash

# 3. Action サーバ起動
ros2 run audio_generator tts_action_server

# 4. 別ターミナルでゴール送信
source ~/ros2_ws/install/setup.bash
ros2 action send_goal --feedback /speak_text audio_generator_interfaces/action/SpeakText \
"{text: 'テスト', speaker_id: -1, playback: true, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}"
``` -->