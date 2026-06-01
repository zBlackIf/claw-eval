cmake_minimum_required(VERSION 3.16)
project(TitanDev VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Development environment flag
add_definitions(-DDEV_ENV)

# ============================================================================
# htvclone module
# ============================================================================
add_library(htvclone STATIC
    htvclone/src/clone_manager.cpp
)
target_include_directories(htvclone PUBLIC
    htvclone/include
    lib/loglib
)

# ============================================================================
# htvstartsequence module
# ============================================================================
add_library(htvstartsequence STATIC
    htvstartsequence/states/base_state.cpp
    htvstartsequence/states/state_goto_off.cpp
    htvstartsequence/states/state_screen_saver.cpp
    htvstartsequence/states/state_boot_sequence.cpp
    htvstartsequence/manager/sequence_manager.cpp
)
target_include_directories(htvstartsequence PUBLIC
    htvstartsequence/include
    htvstartsequence/bean
    htvstartsequence/states
    htvstartsequence/manager
    htvstartsequence/event
)

# ============================================================================
# Main executable (for testing)
# ============================================================================
add_executable(titan_main main.cpp)
target_link_libraries(titan_main PRIVATE htvstartsequence htvclone)
