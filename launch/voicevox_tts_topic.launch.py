from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='voicevox_tts_ros2',
            executable='tts_topic_node',
            name='tts_topic_node',
            output='screen',
            parameters=[{
                'engine_url': 'http://127.0.0.1:50021',
                'speaker_id': 3,
                'speed': 1.0,
                'pitch': 0.0,
                'intonation': 1.0,
                'volume': 1.0,
                'enable_interrogative_upspeak': True,
                'enable_katakana_english': True,
                'playback': True,
                'output_directory': '~/ros2_ws/src/voicevox_tts_ros2'
            }]
        )
    ])