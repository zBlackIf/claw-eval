/**
 * @file main.cpp
 * @brief Test main for state machine startup sequence
 */

#include "htvstartsequence/manager/sequence_manager.h"
#include "htvstartsequence/event/state_event.h"
#include <iostream>

int main() {
    StartSequenceManager::SequenceManager manager;
    manager.initialize();

    // Simulate boot events
    StartSequenceManager::Event bootEvent(StartSequenceManager::EventType::BOOT_COMPLETE);
    manager.dispatchEvent(bootEvent);

    StartSequenceManager::Event channelEvent(StartSequenceManager::EventType::CHANNEL_READY);
    manager.dispatchEvent(channelEvent);

    std::cout << "Current state: " << manager.getCurrentState()->getName() << std::endl;
    return 0;
}
