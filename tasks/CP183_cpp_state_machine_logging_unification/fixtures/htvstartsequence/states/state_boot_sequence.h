/**
 * @file state_boot_sequence.h
 * @brief Boot sequence state - handles system startup logic
 */

#pragma once

#include "base_state.h"

namespace StartSequenceManager {

class StateBootSequence : public BaseState {
public:
    StateBootSequence(SequenceManager* manager, TvSettingsWrapper* settings);

    void enter() override;
    void exit() override;
    bool processEvent(const Event& event) override;
    std::string getName() const override;

private:
    bool m_channelReady;
    bool m_bootComplete;
    int m_retryCount;
};

} // namespace StartSequenceManager
