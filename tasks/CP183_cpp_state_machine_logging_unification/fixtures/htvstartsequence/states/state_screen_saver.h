/**
 * @file state_screen_saver.h
 * @brief ScreenSaver state - handles screen saver activation and timeout
 */

#pragma once

#include "base_state.h"

namespace StartSequenceManager {

class StateScreenSaver : public BaseState {
public:
    StateScreenSaver(SequenceManager* manager, TvSettingsWrapper* settings);

    void enter() override;
    void exit() override;
    bool processEvent(const Event& event) override;
    std::string getName() const override;

private:
    bool m_isActive;
    int m_timeoutSeconds;
};

} // namespace StartSequenceManager
