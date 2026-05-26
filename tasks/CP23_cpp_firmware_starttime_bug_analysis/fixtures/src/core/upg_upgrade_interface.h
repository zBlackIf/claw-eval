#pragma once
#include <string>

class UpgUpgradeInterface {
public:
    UpgUpgradeInterface() = default;
    ~UpgUpgradeInterface() = default;

    bool initialize(const std::string& deviceId);
    bool uploadFirmware(const std::string& path, int timeoutMs);
    std::string getInstalledVersion() const;
    void finalize();

private:
    std::string m_deviceId;
    bool m_initialized = false;
};
