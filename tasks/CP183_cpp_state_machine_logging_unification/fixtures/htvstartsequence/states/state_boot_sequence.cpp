/**
 * @file state_boot_sequence.cpp
 * @brief Implementation of StateBootSequence
 */

#include "state_boot_sequence.h"

namespace StartSequenceManager {

StateBootSequence::StateBootSequence(SequenceManager* manager, TvSettingsWrapper* settings)
    : BaseState(manager, settings), m_channelReady(false), m_bootComplete(false), m_retryCount(0) {}

void StateBootSequence::enter() {
    log("Boot sequence started");
    m_channelReady = false;
    m_bootComplete = false;
    m_retryCount = 0;
}

void StateBootSequence::exit() {
    log("Boot sequence completed, channels_ready=" + std::string(m_channelReady ? "true" : "false"));
}

bool StateBootSequence::processEvent(const Event& event) {
    switch (event.getType()) {
        case EventType::CHANNEL_READY:
            m_channelReady = true;
            log("Channel ready signal received");
            if (m_bootComplete) {
                log("All boot conditions met, transitioning");
                return true;
            }
            break;
        case EventType::BOOT_COMPLETE:
            m_bootComplete = true;
            logDebug("Boot complete signal received");
            if (m_channelReady) {
                log("All boot conditions met, transitioning");
                return true;
            }
            break;
        case EventType::SYSTEM_ERROR:
            m_retryCount++;
            logError("System error during boot, retry=" + std::to_string(m_retryCount));
            if (m_retryCount > 3) {
                logError("Max retries exceeded, entering error state");
                return true;
            }
            break;
        default:
            logDebug("Ignoring event in boot sequence");
            break;
    }
    return false;
}

std::string StateBootSequence::getName() const {
    return "StateBootSequence";
}

} // namespace StartSequenceManager
