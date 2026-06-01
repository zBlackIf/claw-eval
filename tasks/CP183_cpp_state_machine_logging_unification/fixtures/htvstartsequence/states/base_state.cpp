/**
 * @file base_state.cpp
 * @brief Implementation of BaseState
 */

#include "base_state.h"
#include "../manager/sequence_manager.h"
#include <iostream>
#include <chrono>
#include <iomanip>

namespace StartSequenceManager {

BaseState::BaseState(SequenceManager* manager, TvSettingsWrapper* settings)
    : m_manager(manager), m_settings(settings) {}

std::string BaseState::getName() const {
    return "BaseState";
}

void BaseState::log(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::cout << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S")
              << "][INFO][" << getName() << "] " << message << std::endl;
}

void BaseState::logError(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::cerr << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S")
              << "][ERROR][" << getName() << "] " << message << std::endl;
}

void BaseState::logDebug(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::cout << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S")
              << "][DEBUG][" << getName() << "] " << message << std::endl;
}

bool BaseState::readNvmBool(const std::string& key, bool defaultValue) {
    // Stub: in real system this reads from NVM
    return defaultValue;
}

int BaseState::readNvmInt(const std::string& key, int defaultValue) {
    // Stub: in real system this reads from NVM
    return defaultValue;
}

} // namespace StartSequenceManager
