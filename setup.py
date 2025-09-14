from setuptools import setup, find_packages
from pathlib import Path

package_name = 'audio_generator'

# launch フォルダ内の *.py をすべてデータファイルとしてインストール
launch_dir = Path(__file__).parent / 'launch'
launch_files = []
if launch_dir.exists():
    launch_files = [str(p) for p in launch_dir.glob('*.py')]

data_files = [
    ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
    ('share/' + package_name, ['package.xml', 'README.md']),
    ('share/' + package_name + '/launch', launch_files),
]

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=[]),
    data_files=data_files,
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