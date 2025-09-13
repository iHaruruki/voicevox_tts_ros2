cmake_minimum_required(VERSION 3.8)
project(audio_generator)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(rclpy REQUIRED)

# 1) action 生成 (audio_generator 名前空間)
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Tts.action"
  DEPENDENCIES builtin_interfaces
)

# 2) 実装コードは別 Python パッケージ名 audio_generator_runtime としてインストール
ament_python_install_package(audio_generator_runtime)

# 3) 実行スクリプト
install(PROGRAMS
  scripts/audio_generator_action_server
  scripts/tts_action_client_example.py
  DESTINATION lib/${PROJECT_NAME}
)

# 4) 資源
install(DIRECTORY
  launch
  action
  DESTINATION share/${PROJECT_NAME}
)

install(FILES
  requirements.txt
  README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()