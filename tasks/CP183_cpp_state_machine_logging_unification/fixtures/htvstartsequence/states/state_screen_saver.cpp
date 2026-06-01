/**
 * @file state_screen_saver.cpp
 * @brief Implementation of StateScreenSaver
 */

#include "state_screen_saver.h"

namespace StartSequenceManager {

StateScreenSaver::StateScreenSaver(SequenceManager* manager, TvSettingsWrapper* settings)
    : BaseState(manager, settings), m_isActive(false), m_timeoutSeconds(300) {}

void StateScreenSaver::enter() {
    m_isActive = true;
    m_timeoutSeconds = readNvmInt("screensaver_timeout", 300);
    log("ScreenSaver activated, timeout=" + std::to_string(m_timeoutSeconds) + "s");
}

void StateScreenSaver::exit() {
    m_isActive = false;
    log("ScreenSaver deactivated");
}

bool StateScreenSaver::processEvent(const Event& event) {
    if (event.getType() == EventType::USER_INPUT) {
        log("User input received, exiting screen saver");
        return true;
    }
    if (event.getType() == EventType::SCREEN_SAVER_TIMEOUT) {
        logDebug("Screen saver timeout - transitioning to power off");
        return true;
    }
    return false;
}

std::string StateScreenSaver::getName() const {
    return "StateScreenSaver";
}

} // namespace StartSequenceManager
