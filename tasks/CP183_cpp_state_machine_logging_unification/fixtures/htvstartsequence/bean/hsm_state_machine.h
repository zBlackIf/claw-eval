/**
 * @file hsm_state_machine.h
 * @brief Hierarchical State Machine manager
 */

#pragma once

#include "hsm_state.h"
#include <memory>
#include <vector>
#include <iostream>

namespace StartSequenceManager {

/**
 * @brief HSM state machine - manages state transitions
 */
class HsmStateMachine {
public:
    HsmStateMachine() : m_currentState(nullptr) {}

    void setInitialState(State* state) {
        m_currentState = state;
        if (m_currentState) {
            std::cout << "[HSM] Entering initial state: " << m_currentState->getName() << std::endl;
            m_currentState->enter();
        }
    }

    void transitionTo(State* newState) {
        if (m_currentState) {
            std::cout << "[HSM] Exiting state: " << m_currentState->getName() << std::endl;
            m_currentState->exit();
        }
        m_currentState = newState;
        if (m_currentState) {
            std::cout << "[HSM] Entering state: " << m_currentState->getName() << std::endl;
            m_currentState->enter();
        }
    }

    bool dispatchEvent(const Event& event) {
        if (m_currentState) {
            return m_currentState->processEvent(event);
        }
        return false;
    }

    State* getCurrentState() const { return m_currentState; }

private:
    State* m_currentState;
};

} // namespace StartSequenceManager
