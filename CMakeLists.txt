cmake_minimum_required(VERSION 3.8)
project(audio_generator)

# 必要パッケージ
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(rclpy REQUIRED)

# Python パッケージをインストール
ament_python_install_package(${PROJECT_NAME})

# アクション生成
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Tts.action"
  DEPENDENCIES builtin_interfaces
)

# 実行スクリプト（ラッパ）
install(PROGRAMS
  scripts/audio_generator_action_server
  scripts/tts_action_client_example.py
  DESTINATION lib/${PROJECT_NAME}
)

# launch, action, 資料類
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