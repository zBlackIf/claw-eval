/**
 * @file base_state.h
 * @brief Base class for all business states
 *
 * Provides access to SequenceManager and TvSettingsWrapper,
 * all concrete states should inherit from this class.
 */

#pragma once

#include "../bean/hsm_state.h"
#include <string>
#include <memory>

namespace StartSequenceManager {

// Forward declarations
class SequenceManager;
class TvSettingsWrapper;

/**
 * @brief Base class for all business states
 * @details Provides custom logging and access to SequenceManager/TvSettingsWrapper.
 */
class BaseState : public State {
public:
    BaseState(SequenceManager* manager, TvSettingsWrapper* settings);
    virtual ~BaseState() = default;

    BaseState(const BaseState&) = delete;
    BaseState& operator=(const BaseState&) = delete;

    SequenceManager* getManager() const { return m_manager; }
    TvSettingsWrapper* getSettings() const { return m_settings; }

    // Logging methods
    void log(const std::string& message);
    void logError(const std::string& message);
    void logDebug(const std::string& message);

    virtual std::string getName() const override;

protected:
    SequenceManager* m_manager;
    TvSettingsWrapper* m_settings;

    bool readNvmBool(const std::string& key, bool defaultValue = false);
    int readNvmInt(const std::string& key, int defaultValue = 0);
};

} // namespace StartSequenceManager
