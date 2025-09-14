# audio_generator

`audio_generator_node` は `std_msgs/msg/String` のテキストを購読し、VOICEVOX エンジンで音声合成した WAV を保存・必要に応じて再生します。

## 前提

- ROS 2 Humble 環境
- VOICEVOX エンジン (例: `docker run -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest` など)
- Python 依存  
  ```bash
  pip install requests simpleaudio
  ```  
  simpleaudio が不要・インストールできない場合はフォールバック再生を利用します。

## ビルド

```bash
cd ~/ros2_ws/src
# 本パッケージを配置
colcon build --packages-select audio_generator
source ~/ros2_ws/install/setup.bash
```

## 起動

```bash
ros2 launch audio_generator audio_generator_launch.py
```

## トピック送信例

```bash
ros2 topic pub /tts_text std_msgs/String "data: 'こんにちは、テストです。'"
```

### Action Usage

```bash
ros2 run audio_generator tts_action_server
ros2 action send_goal --feedback /speak_text audio_generator_interfaces/action/SpeakText '{text: "テスト", speaker_id: -1, playback: true, speed: 0.0, pitch: 0.0, intonation: 0.0, volume: 0.0, allow_cache: true}'
```

## 動的パラメータ変更例

```bash
ros2 param set /audio_generator_node speaker_id 1
ros2 param set /audio_generator_node speed 1.2
ros2 param set /audio_generator_node playback false
```

## パラメータ一覧

| 名前 | 型 | 説明 | 既定値 |
|------|----|------|--------|
| engine_url | string | VOICEVOX エンジンURL | http://127.0.0.1:50021 |
| speaker_id | int | 話者ID | 3 |
| speed | double | speedScale | 1.0 |
| pitch | double | pitchScale | 0.0 |
| intonation | double | intonationScale | 1.0 |
| volume | double | volumeScale | 1.0 |
| enable_interrogative_upspeak | bool | 疑問形末上げ | true |
| enable_katakana_english | bool | 英単語カタカナ化 | true |
| playback | bool | 自動再生有無 | true |
| output_directory | string | WAV保存先 | /tmp/audio_generator |

## 拡張アイデア

- 合成完了を別トピックで通知 (例: `std_msgs/String` でファイルパス通知)
- Service や Action を追加し同期呼び出しに対応
- テキスト内のメタタグ (例: `[spk=2]`) をパースして話者切替

## ライセンス
MIT