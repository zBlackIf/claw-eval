/**
 * @file hsm_state.h
 * @brief Hierarchical State Machine - State base class
 */

#pragma once

#include <string>

namespace StartSequenceManager {

class Event;

/**
 * @brief Abstract base class for HSM states
 */
class State {
public:
    virtual ~State() = default;

    virtual void enter() = 0;
    virtual void exit() = 0;
    virtual bool processEvent(const Event& event) = 0;
    virtual std::string getName() const = 0;
};

} // namespace StartSequenceManager
