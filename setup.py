from setuptools import setup
from pathlib import Path

package_name = 'audio_generator'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/action', ['action/Tts.action']),
        ('share/' + package_name + '/launch', ['launch/audio_generator_action.launch.py']),
        ('share/' + package_name, ['requirements.txt', 'README.md']),
        ('share/' + package_name + '/scripts', ['scripts/tts_action_client_example.py'])
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='ROS2 VOICEVOX TTS action server (memory only).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'audio_generator_action_server = audio_generator.audio_generator_action_server:main',
        ],
    },
)