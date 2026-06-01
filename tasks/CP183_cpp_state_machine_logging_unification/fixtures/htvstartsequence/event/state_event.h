/**
 * @file state_event.h
 * @brief Event definitions for the state machine
 */

#pragma once

#include <string>
#include <any>

namespace StartSequenceManager {

enum class EventType {
    POWER_ON,
    CHANNEL_READY,
    SCREEN_SAVER_TIMEOUT,
    USER_INPUT,
    SYSTEM_ERROR,
    BOOT_COMPLETE
};

class Event {
public:
    Event(EventType type) : m_type(type) {}
    Event(EventType type, const std::string& data) : m_type(type), m_data(data) {}

    EventType getType() const { return m_type; }
    std::string getData() const { return m_data; }

private:
    EventType m_type;
    std::string m_data;
};

} // namespace StartSequenceManager
