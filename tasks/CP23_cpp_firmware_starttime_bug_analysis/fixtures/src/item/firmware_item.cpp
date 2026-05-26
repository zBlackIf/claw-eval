#include "firmware_item.h"
#include "../utils/logger.h"
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

FirmwareItem::FirmwareItem(const FirmwareConfig& config)
    : m_config(config)
    , m_upgrader(std::make_unique<UpgUpgradeInterface>())
{
    m_itemId = "FW_" + config.targetDevice + "_" + config.version;
}

// BUG: This override does NOT call ICloneItem::preExecuteItem()
// Therefore m_startTime is never set
bool FirmwareItem::preExecuteItem() {
    LOG_INFO("FirmwareItem::preExecuteItem - validating firmware: " + m_config.firmwarePath);

    m_status = ItemStatus::PREPARING;

    if (!fs::exists(m_config.firmwarePath)) {
        m_errorMsg = "Firmware file not found: " + m_config.firmwarePath;
        LOG_ERROR(m_errorMsg);
        return false;
    }

    if (!validateFirmware()) {
        m_errorMsg = "Firmware validation failed";
        LOG_ERROR(m_errorMsg);
        return false;
    }

    if (!m_upgrader->initialize(m_config.targetDevice)) {
        m_errorMsg = "Failed to initialize upgrade interface for device: " + m_config.targetDevice;
        LOG_ERROR(m_errorMsg);
        return false;
    }

    m_progress = 0;
    LOG_INFO("FirmwareItem::preExecuteItem - preparation complete");
    return true;
}

bool FirmwareItem::executeItem() {
    LOG_INFO("FirmwareItem::executeItem - starting firmware transfer");
    m_status = ItemStatus::EXECUTING;

    if (!transferFirmware()) {
        onError("Firmware transfer failed");
        return false;
    }

    if (!verifyInstallation()) {
        onError("Firmware verification failed after transfer");
        return false;
    }

    m_progress = 100;
    if (m_progressCb) m_progressCb(100);
    return true;
}

void FirmwareItem::postExecuteItem() {
    ICloneItem::postExecuteItem();
    m_upgrader->finalize();
    LOG_INFO("FirmwareItem complete. Start: " + m_startTime + " End: " + m_endTime);
}

bool FirmwareItem::validateFirmware() {
    std::ifstream file(m_config.firmwarePath, std::ios::binary);
    if (!file.good()) return false;

    // Check magic bytes
    char magic[4];
    file.read(magic, 4);
    if (magic[0] != 'F' || magic[1] != 'W') return false;

    // Check file size
    file.seekg(0, std::ios::end);
    auto size = file.tellg();
    if (size < 1024 || size > 512 * 1024 * 1024) return false;

    return true;
}

bool FirmwareItem::transferFirmware() {
    int retries = m_config.retryCount;
    while (retries > 0) {
        if (m_upgrader->uploadFirmware(m_config.firmwarePath, m_config.timeoutMs)) {
            return true;
        }
        retries--;
        LOG_WARN("Transfer failed, retries left: " + std::to_string(retries));
    }
    return false;
}

bool FirmwareItem::verifyInstallation() {
    auto installedVersion = m_upgrader->getInstalledVersion();
    return installedVersion == m_config.version;
}
