#include "firmware_item.h"
#include "../utils/logger.h"
#include "../utils/clone_config.h"
#include "../utils/file_utils.h"
#include "../helper/identifier_helper.h"
#include "../history/history_manager_factory.h"
#include "../core/upg_upgrade_interface.h"
#include "error_code.h"
#include <vector>
#include <string>
#include <filesystem>

#define LOG_TAG "FirmwareItem"

namespace CloneMgrMw {

const std::vector<std::string>& FirmwareItem::getFilesToCopy() const {
    static const std::vector<std::string> FILES_TO_COPY = {};
    return FILES_TO_COPY;
}

FirmwareItem::FirmwareItem() {
}

FirmwareItem::~FirmwareItem() {
}

CloneItemType FirmwareItem::getItemType() const {
    return CloneItemType::ITEM_FIRMWARE;
}

ErrorCode FirmwareItem::preExecuteItem(
    CloneActionType actionType,
    std::function<bool()> cancelCheckCallback) {
    LOG_INFO(LOG_TAG, "preExecuteItem - Action: %s",
             getActionTypeName(actionType).c_str());
    
    if (ICloneItem::isCloneIn(actionType)) {
        // 记录开始时间
        m_startTime = IdentifierHelper::getDateTimeString();

        std::string sourcePath = CloneConfig::getInstance().getOtaPackagePath();

        if(ICloneItem::isUsbCloneIn(actionType)) {
            sourcePath = CloneConfig::getInstance().getItemDataPath(getItemType());
        } else if(ICloneItem::isIPCloneIn(actionType)) {
            sourcePath = CloneConfig::getInstance().getOtaPackagePath();
        }

        LOG_INFO(LOG_TAG, "Checking for .upg files in: %s", sourcePath.c_str());
        
        m_firmwarePath = findFirmwareInDirectory(sourcePath);
        if (m_firmwarePath.empty()) {
            LOG_ERROR(LOG_TAG, "No valid .upg file found in source path: %s", sourcePath.c_str());
            return ErrorCode::ERROR_ITEM_NOT_AVAILABLE;
        }
        
        LOG_INFO(LOG_TAG, "Found firmware file: %s", m_firmwarePath.c_str());
    } else {
        LOG_INFO(LOG_TAG, "Clone Out action does not supported for Firmware");
        return ErrorCode::ERROR_ITEM_NOT_AVAILABLE;
    }
    
    return ErrorCode::SUCCESS;
}

ErrorCode FirmwareItem::doCloneIn(
    CloneActionType actionType,
    std::function<void(int progress)> progressCallback,
    std::function<bool()> cancelCheckCallback) {
    LOG_INFO(LOG_TAG, "doCloneIn - Action: %s", 
             getActionTypeName(actionType).c_str());
    
    if (m_firmwarePath.empty()) {
        LOG_ERROR(LOG_TAG, "Firmware path not found. preExecuteItem must be called first.");
        return ErrorCode::ERROR_ITEM_NOT_AVAILABLE;
    }
    
    if (!std::filesystem::exists(m_firmwarePath)) {
        LOG_ERROR(LOG_TAG, "Firmware file does not exist: %s", m_firmwarePath.c_str());
        return ErrorCode::ERROR_ITEM_NOT_AVAILABLE;
    }
    
    LOG_INFO(LOG_TAG, "Using firmware file: %s", m_firmwarePath.c_str());

    // Check firmware if valid
    ErrorCode verifyResult = UpgUpgradeInterface::getInstance().verifyFirmware(m_firmwarePath);
    if (verifyResult != ErrorCode::SUCCESS) {
        LOG_INFO(LOG_TAG, "Verify firmware failed with error: %d", static_cast<int>(verifyResult));
        return verifyResult;
    }

    
    ErrorCode upgradeResult = UpgUpgradeInterface::getInstance().startUpgrade(m_firmwarePath);
    if (upgradeResult != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "Firmware upgrade failed with error: %d", 
                 static_cast<int>(upgradeResult));
        return upgradeResult;
    }

    // TODO: Need create flag file to indicate FW reboot happened. 
    // And after reboot, check the flag file to continue other clone items
    
    LOG_INFO(LOG_TAG, "Firmware upgrade completed successfully");
    return ErrorCode::SUCCESS;
}

ErrorCode FirmwareItem::doCloneOut(
    CloneActionType actionType,
    std::function<void(int progress)> progressCallback,
    std::function<bool()> cancelCheckCallback) {
    LOG_INFO(LOG_TAG, "doCloneOut - Action: %s",
             getActionTypeName(actionType).c_str());
    
    LOG_DEBUG(LOG_TAG, "doCloneOut - Clone Out action does not supported for Firmware");
    
    return ErrorCode::ERROR_ITEM_NOT_AVAILABLE;
}

bool FirmwareItem::shouldCompress(CloneActionType actionType) const {
    return true;
}

ErrorCode FirmwareItem::clearData(const std::string& clearReason) {
    LOG_INFO(LOG_TAG, "clearData - Firmware does not support Identifier/History");
    return ErrorCode::SUCCESS;
}

bool FirmwareItem::isDataAvailable(CloneActionType actionType) const {
    return true;
}

std::string FirmwareItem::getHistoryFileName() const {
    // Firmware 没有 History 文件
    return "Firmware_History.xml";
}

std::string FirmwareItem::getIdentifierFileName() const {
    return "Firmware_Identifier.txt";
}

bool FirmwareItem::hasHistorySupport() const {
    return false;
}

bool FirmwareItem::hasIdentifierSupport() const {
    return false;
}

std::string FirmwareItem::findFirmwareInDirectory(const std::string& directoryPath) const {
    LOG_INFO(LOG_TAG, "findFirmwareInDirectory - Searching for .upg files in: %s", directoryPath.c_str());
    
    // 检查目录是否存在
    if (!std::filesystem::exists(directoryPath)) {
        LOG_ERROR(LOG_TAG, "Directory does not exist: %s", directoryPath.c_str());
        return "";
    }
    
    int upgFileCount = 0;
    std::string foundFirmwarePath;
    
    try {
        for (const auto& entry : std::filesystem::directory_iterator(directoryPath)) {
            if (entry.is_regular_file() && entry.path().extension() == ".upg") {
                upgFileCount++;
                foundFirmwarePath = entry.path().string();
                LOG_DEBUG(LOG_TAG, "Found .upg file: %s", entry.path().filename().c_str());
            }
        }
    } catch (const std::filesystem::filesystem_error& e) {
        LOG_ERROR(LOG_TAG, "Filesystem error when scanning directory %s: %s", 
                 directoryPath.c_str(), e.what());
        return "";
    }
    
    LOG_INFO(LOG_TAG, "Found %d .upg file(s) in directory", upgFileCount);
    
    if (upgFileCount == 0) {
        LOG_ERROR(LOG_TAG, "No .upg files found in directory: %s", directoryPath.c_str());
        return "";
    }
    
    if (upgFileCount > 1) {
        LOG_ERROR(LOG_TAG, "Multiple .upg files found in directory: %s (found %d files)", 
                 directoryPath.c_str(), upgFileCount);
        return "";
    }
    
    // 找到恰好一个 .upg 文件
    LOG_INFO(LOG_TAG, "Found exactly one .upg file: %s", foundFirmwarePath.c_str());
    return foundFirmwarePath;
}


ErrorCode FirmwareItem::finishItem(CloneActionType actionType, CloneStatus cloneStatus) {
    LOG_INFO(LOG_TAG, "finishItem - Writing firmware version info to IDT and History, Status: %s",
             getStatusName(cloneStatus).c_str());


    if(ICloneItem::isCloneOut(actionType)) {
        LOG_INFO(LOG_TAG, "Firmware item doesn't support Clone Out finish action");
        return ErrorCode::SUCCESS;
    }

    m_endTime = IdentifierHelper::getDateTimeString();
    std::string firmwareVersion = UpgUpgradeInterface::getInstance().getFirmwareVersion();
    
    if (!firmwareVersion.empty()) {
        LOG_INFO(LOG_TAG, "Using stored firmware version: %s", firmwareVersion.c_str());

        // Save last clone status to database
        IdentifierHelper::writeLastStatusToDb(getItemType(), getStatusName(cloneStatus));
        IdentifierHelper::writeStartTimeToDb(getItemType(), m_startTime);
        IdentifierHelper::writeEndTimeToDb(getItemType(), m_endTime);

        std::string identifier = IdentifierHelper::getNewIdentifier();
        IdentifierHelper::writeIdentifierToDb(getItemType(), identifier);

        // Only update Firmware History to DB
        if(!CloneConfig::getInstance().useXmlForHistory()) {
            std::string historyFileName = getHistoryFileName();
            std::string historyFilePath = CloneConfig::getInstance().getCloneHistoryPath() + "/" + historyFileName;
            std::string tvHistoryPath = CloneConfig::getInstance().getCloneHistoryPath() + "/" + historyFileName;

            auto& historyManager = HistoryManagerFactory::getInstance(
                CloneConfig::getInstance().useXmlForHistory()
            );
            
            ErrorCode result = historyManager.mergeHistory(
                historyFilePath,
                tvHistoryPath,
                getItemType(),
                "FirmwareUpgrade");
            
            if (result != ErrorCode::SUCCESS) {
                LOG_ERROR(LOG_TAG, "doCloneInHistory - mergeHistory failed: %d", 
                        static_cast<int>(result));
            }
        }
        
        LOG_INFO(LOG_TAG, "Firmware upgrade version %s recorded to IDT and History", 
                firmwareVersion.c_str());
    } else {
        LOG_ERROR(LOG_TAG, "No firmware version found to record");
    }
    
    return ErrorCode::SUCCESS;
}

}