from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='audio_generator',
            executable='audio_generator_action_server',
            name='audio_generator_action_server',
            parameters=[{
                'engine_url': 'http://127.0.0.1:50021',
                'default_speaker_id': 3,
                'default_speed': 1.0,
                'default_pitch': 0.0,
                'default_intonation': 1.0,
                'default_volume': 1.0
            }]
        )
    ])