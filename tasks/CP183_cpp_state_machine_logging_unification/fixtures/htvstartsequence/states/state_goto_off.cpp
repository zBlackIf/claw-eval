/**
 * @file state_goto_off.cpp
 * @brief Implementation of StateGotoOff
 */

#include "state_goto_off.h"

namespace StartSequenceManager {

StateGotoOff::StateGotoOff(SequenceManager* manager, TvSettingsWrapper* settings)
    : BaseState(manager, settings) {}

void StateGotoOff::enter() {
    log("StateGotoOff::enter() - anchor state, no action");
}

void StateGotoOff::exit() {
    log("StateGotoOff::exit() - anchor state, no action");
}

bool StateGotoOff::processEvent(const Event& event) {
    logDebug("StateGotoOff does not handle any events");
    return false;
}

std::string StateGotoOff::getName() const {
    return "StateGotoOff";
}

std::string StateGotoOff::getDescription() const {
    return "Empty anchor state for state machine initialization";
}

} // namespace StartSequenceManager
