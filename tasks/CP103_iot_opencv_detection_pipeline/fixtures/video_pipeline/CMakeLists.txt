cmake_minimum_required(VERSION 3.14)
project(video_pipeline CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(video_pipeline
    main.cpp
    visualizer.cpp
    json_exporter.cpp
    yolo_detector_acl.cpp
)

target_link_libraries(video_pipeline ${OpenCV_LIBS})
