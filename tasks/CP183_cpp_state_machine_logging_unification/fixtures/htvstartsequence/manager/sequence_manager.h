/**
 * @file sequence_manager.h
 * @brief SequenceManager - orchestrates state transitions for TV startup
 */

#pragma once

#include "../bean/hsm_state_machine.h"
#include <string>
#include <memory>
#include <vector>
#include <iostream>

namespace StartSequenceManager {

class TvSettingsWrapper;
class BaseState;

/**
 * @brief Manages the startup sequence state machine
 */
class SequenceManager {
public:
    SequenceManager();
    ~SequenceManager() = default;

    void initialize();
    void dispatchEvent(const Event& event);
    State* getCurrentState() const;

    void log(const std::string& message);
    void logError(const std::string& message);

private:
    HsmStateMachine m_stateMachine;
    std::vector<std::unique_ptr<BaseState>> m_states;
    TvSettingsWrapper* m_settings;
};

} // namespace StartSequenceManager
