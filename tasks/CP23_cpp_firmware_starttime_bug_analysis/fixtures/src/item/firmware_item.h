#pragma once
#include "iclone_item.h"
#include "../core/upg_upgrade_interface.h"
#include <vector>
#include <functional>

struct FirmwareConfig {
    std::string firmwarePath;
    std::string targetDevice;
    std::string version;
    int retryCount = 3;
    int timeoutMs = 30000;
};

class FirmwareItem : public ICloneItem {
public:
    explicit FirmwareItem(const FirmwareConfig& config);
    ~FirmwareItem() override = default;

    bool preExecuteItem() override;
    bool executeItem() override;
    void postExecuteItem() override;

    void setProgressCallback(std::function<void(int)> cb) { m_progressCb = std::move(cb); }
    int getProgress() const { return m_progress; }
    std::string getFirmwareVersion() const { return m_config.version; }

private:
    bool validateFirmware();
    bool transferFirmware();
    bool verifyInstallation();

    FirmwareConfig m_config;
    std::unique_ptr<UpgUpgradeInterface> m_upgrader;
    int m_progress = 0;
    std::function<void(int)> m_progressCb;
};
