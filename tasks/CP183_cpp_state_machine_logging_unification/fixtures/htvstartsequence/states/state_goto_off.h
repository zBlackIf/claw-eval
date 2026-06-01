/**
 * @file state_goto_off.h
 * @brief StateGotoOff - Empty anchor state for state machine initialization
 */

#pragma once

#include "base_state.h"

namespace StartSequenceManager {

class StateGotoOff : public BaseState {
public:
    StateGotoOff(SequenceManager* manager, TvSettingsWrapper* settings);

    void enter() override;
    void exit() override;
    bool processEvent(const Event& event) override;
    std::string getName() const override;
    std::string getDescription() const;

private:
    // Intentionally empty - this is an anchor state
};

} // namespace StartSequenceManager
