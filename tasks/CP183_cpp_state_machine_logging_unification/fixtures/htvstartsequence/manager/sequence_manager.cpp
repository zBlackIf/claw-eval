/**
 * @file sequence_manager.cpp
 * @brief Implementation of SequenceManager
 */

#include "sequence_manager.h"
#include "../states/state_goto_off.h"
#include "../states/state_screen_saver.h"
#include "../states/state_boot_sequence.h"
#include <iostream>
#include <chrono>
#include <iomanip>

namespace StartSequenceManager {

SequenceManager::SequenceManager() : m_settings(nullptr) {}

void SequenceManager::initialize() {
    log("SequenceManager initializing");

    // Create states
    auto gotoOff = std::make_unique<StateGotoOff>(this, m_settings);
    auto bootSeq = std::make_unique<StateBootSequence>(this, m_settings);
    auto screenSaver = std::make_unique<StateScreenSaver>(this, m_settings);

    // Set initial state
    m_stateMachine.setInitialState(gotoOff.get());

    // Store ownership
    m_states.push_back(std::move(gotoOff));
    m_states.push_back(std::move(bootSeq));
    m_states.push_back(std::move(screenSaver));

    log("SequenceManager initialized with " + std::to_string(m_states.size()) + " states");
}

void SequenceManager::dispatchEvent(const Event& event) {
    m_stateMachine.dispatchEvent(event);
}

State* SequenceManager::getCurrentState() const {
    return m_stateMachine.getCurrentState();
}

void SequenceManager::log(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::cout << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S")
              << "][INFO][SequenceManager] " << message << std::endl;
}

void SequenceManager::logError(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::cerr << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S")
              << "][ERROR][SequenceManager] " << message << std::endl;
}

} // namespace StartSequenceManager
