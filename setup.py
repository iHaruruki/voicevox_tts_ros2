import os
from glob import glob
from setuptools import setup, find_packages
from pathlib import Path

package_name = 'voicevox_tts_ros2'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=[]),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*')),
    ],
    install_requires=[
        'setuptools',
        'requests',
        # 'simpleaudio',  # 任意
    ],
    zip_safe=True,
    maintainer='Haruki Isono',
    maintainer_email='haruki.isono861@gmail.com',
    description='Subscribe to text topic and generate audio via VOICEVOX.',
    license='Todo',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tts_topic_node = voicevox_tts_ros2.tts_topic:main',
            'tts_action_server = voicevox_tts_ros2.tts_action_server:main',
            'tts_action_client = voicevox_tts_ros2.tts_action_client:main',
        ],
    },
)