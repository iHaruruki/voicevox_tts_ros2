import os
from glob import glob
from setuptools import setup, find_packages
from pathlib import Path

package_name = 'audio_generator'

setup(
    name=package_name,
    version='0.0.1',
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
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='Subscribe to text topic and generate audio via VOICEVOX.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'audio_generator_node = audio_generator.audio_generator_node:main',
        ],
    },
)