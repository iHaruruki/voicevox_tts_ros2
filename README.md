# audio_generator (v1.0.0 Memory-Only / Action-based)

VOICEVOX を利用した ROS 2 Humble 用 TTS アクションサーバ。  
ディスクへ WAV を保存せずメモリ上で合成・再生し、必要に応じてバイト列を返します。

## 変更点 (旧バージョンからの移行)

- 旧サービス `Tts.srv` / ノード `audio_generator_node` を廃止
- アクション `Tts.action` に統合 (進捗・キャンセル可能)
- フィードバックでフェーズ進捗を通知
- メモリ再生: `simpleaudio` → `pyaudio` → 無し(警告) の順に試行
- ファイル永続化は行わない（必要であればクライアント側で `wav_data` を保存）

## Action: /audio_generator

Goal:
| Field        | Type    | Description |
|--------------|---------|-------------|
| text         | string  | 合成テキスト |
| speaker_id   | int32   | 話者ID (負ならパラメータ default_speaker_id) |
| speed        | float32 | 速度 (>0 で適用, 0以下でデフォルト) |
| pitch        | float32 | ピッチ (0.0 の場合デフォルト) |
| intonation   | float32 | 抑揚 (>0 で適用) |
| volume       | float32 | 音量 (>0 で適用) |
| play         | bool    | メモリ再生 |
| return_wav   | bool    | バイト列取得 |

Feedback:
| Field       | Type    | Note |
|-------------|---------|------|
| phase       | uint8   | 0=QUEUED 1=QUERYING 2=SYNTHESIZING 3=PLAYING 4=COMPLETED 5=CANCELED 6=ERROR |
| phase_label | string  | フェーズ名 |
| progress    | float32 | 擬似 0.0～1.0 |
| message     | string  | 補足 |

Result:
| Field     | Type    | Description |
|-----------|---------|-------------|
| success   | bool    | 成功フラグ |
| error     | string  | エラー内容 |
| wav_data  | uint8[] | return_wav=true のとき WAV バイト列 |

## インストール

```
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select audio_generator
. install/setup.bash
pip install -r install/audio_generator/share/audio_generator/requirements.txt
```

`pyaudio` は OS によっては追加で `portaudio` ライブラリが必要です。

## 起動

```
ros2 launch audio_generator audio_generator_action.launch.py
```

## クライアント例 (再生のみ)

```
ros2 run audio_generator tts_action_client_example
```

## Python クライアントで WAV を保存したい場合

`return_wav=true` で受け取った `result.wav_data` をファイルへ:

```python
with open("out.wav", "wb") as f:
    f.write(bytes(result.wav_data))
```

## キャンセル

別ターミナルから:

```
ros2 action list
ros2 action info /audio_generator
ros2 action send_goal /audio_generator audio_generator/action/Tts "{text: '長文...', speaker_id: 3, speed: 1.0, pitch: 0.0, intonation: 1.0, volume: 1.0, play: false, return_wav: false}"
# goal_id を控えた上で:
ros2 action cancel /audio_generator <goal_id>
```

HTTP リクエスト中は即時中断できないため、フェーズ境界でキャンセルが反映されます。

## 制約と今後の拡張余地

- VOICEVOX API はストリーミング非対応のため細粒度進捗は擬似
- 大容量音声頻発ならアクションより専用ストリーム（FastDDS loaned sample / gRPC 等）検討
- フェーズ毎ログ以外に統計（処理時間）を Result に追加可能
- 複数同時合成をリミットしたい場合は内部キュー実装を追加可能

## ライセンス

MIT