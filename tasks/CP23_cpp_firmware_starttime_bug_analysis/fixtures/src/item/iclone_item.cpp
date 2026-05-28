#include "iclone_item.h"
#include "../utils/logger.h"
#include "../utils/clone_config.h"
#include "../utils/file_utils.h"
#include "../history/history_manager_factory.h"
#include "../history/db_history_adapter.h"
#include "../helper/identifier_helper.h"
#include "../helper/db_history_helper.h"
#include <filesystem>
#include <vector>
#include <algorithm>
#include <chrono>
#include <ctime>


#define LOG_TAG "ICloneItem"


namespace CloneMgrMw {

ErrorCode ICloneItem::postExecuteItem(
    CloneActionType actionType,
    std::function<bool()> cancelCheckCallback) {
    
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "postExecuteItem - Item: %s, Action: %s",
             itemTypeName.c_str(), getActionTypeName(actionType).c_str());
    
    if (cancelCheckCallback && cancelCheckCallback()) {
        return ErrorCode::ERROR_OPERATION_CANCELLED;
    }
    
    if(getItemType() == CloneItemType::ITEM_FIRMWARE) {
        LOG_INFO(LOG_TAG, "Firmware item doesn't handle post-execute action");
        return ErrorCode::SUCCESS;
    }

    std::string srcPath = CloneConfig::getInstance().getSrcCloneItemPath(getItemType());
    std::string destPath = CloneConfig::getInstance().getDestCloneItemPath(getItemType());
    
    LOG_INFO(LOG_TAG, "Copying files from Source to Dest: %s -> %s", 
             srcPath.c_str(), destPath.c_str());

    if (!FileUtils::copyFiles(srcPath, destPath, getFilesToCopy())) {
        LOG_ERROR(LOG_TAG, "Failed to copy files from source to destination");
        return ErrorCode::ERROR_FILE_COPY_FAILED;
    }
    
    LOG_INFO(LOG_TAG, "Successfully copied files for item: %s", itemTypeName.c_str());
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::finishItem(CloneActionType actionType, CloneStatus cloneStatus) {
    
    // 记录结束时间
    m_endTime = IdentifierHelper::getDateTimeString();
    
    LOG_INFO(LOG_TAG, "finishItem - Item: %s, Action: %s, Status: %s, StartTime: %s, EndTime: %s",
             getItemTypeName(getItemType()).c_str(),
             getActionTypeName(actionType).c_str(),
             getStatusName(cloneStatus).c_str(),
             m_startTime.c_str(),
             m_endTime.c_str());

    // Save last clone status to database
    IdentifierHelper::writeLastStatusToDb(getItemType(), getStatusName(cloneStatus));
    IdentifierHelper::writeStartTimeToDb(getItemType(), m_startTime);
    IdentifierHelper::writeEndTimeToDb(getItemType(), m_endTime);
    
    
    if (isCloneIn(actionType)) {
        ErrorCode identifierResult = doCloneInIdentifier(actionType);
        if (identifierResult != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Identifier processing failed: %d", 
                     static_cast<int>(identifierResult));
            return identifierResult;
        }

        ErrorCode historyResult = doCloneInHistory(actionType, "CloneIn");
        if (historyResult != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "History processing failed: %d", 
                     static_cast<int>(historyResult));
            return historyResult;
        }
    } else if (isCloneOut(actionType)) {
        ErrorCode identifierResult = doCloneOutIdentifier();
        if (identifierResult != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Identifier processing failed: %d", 
                     static_cast<int>(identifierResult));
            return identifierResult;
        }

        ErrorCode historyResult = doCloneOutHistory();
        if (historyResult != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "History processing failed: %d", 
                     static_cast<int>(historyResult));
            return historyResult;
        }
    }
    
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::doCloneInIdentifier(CloneActionType actionType) {
    
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "doCloneInIdentifier - Processing Identifier for: %s, Action: %s",
             itemTypeName.c_str(), getActionTypeName(actionType).c_str());
    
    if (!hasIdentifierSupport()) {
        LOG_INFO(LOG_TAG, "doCloneInIdentifier - Identifier not supported for item type: %s", 
                 itemTypeName.c_str());
        return ErrorCode::SUCCESS;
    }
    
    std::string sourceIdentifierPath = CloneConfig::getInstance()
            .getSrcCloneItemPath(getItemType()) + "/" + getIdentifierFileName();
    LOG_INFO(LOG_TAG, "Clone In - Source identifier path: %s", sourceIdentifierPath.c_str());
    
    std::string identifier;
    
    if (!IdentifierHelper::isEmptyContent(sourceIdentifierPath)) {
        identifier = IdentifierHelper::readIdentifierFile(sourceIdentifierPath);
        LOG_INFO(LOG_TAG, "Read Identifier from source for %s: %s", 
                 itemTypeName.c_str(), identifier.c_str());
    } else {
        identifier = IdentifierHelper::getNewIdentifier();
        LOG_INFO(LOG_TAG, "Generated new Identifier for %s: %s", 
                 itemTypeName.c_str(), identifier.c_str());
    }
    
    if (!IdentifierHelper::isValidIdentifier(identifier)) {
        LOG_ERROR(LOG_TAG, "Invalid Identifier for %s: %s", 
                  itemTypeName.c_str(), identifier.c_str());
        return ErrorCode::ERROR_IDENTIFIER_INVALID;
    }
    
    bool success = IdentifierHelper::writeIdentifierToDb(getItemType(), identifier);
    if (!success) {
        LOG_ERROR(LOG_TAG, "Failed to write Identifier to database for %s", 
                 itemTypeName.c_str());
        return ErrorCode::ERROR_DATA_SERIALIZE_FAILED;
    }
    
    LOG_INFO(LOG_TAG, "Successfully wrote Identifier to database for %s: %s", 
             itemTypeName.c_str(), identifier.c_str());
    
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::doCloneOutIdentifier() {
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Processing Identifier for: %s", 
             itemTypeName.c_str());
    
    if (!hasIdentifierSupport()) {
        LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Identifier not supported for item type: %s", 
                 itemTypeName.c_str());
        return ErrorCode::SUCCESS;
    }
    
    std::string identifier = IdentifierHelper::readIdentifierFromDb(getItemType());
    if (!identifier.empty()) {
        LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Read Identifier from database for %s: %s", 
                 itemTypeName.c_str(), identifier.c_str());
    } else {
        identifier = IdentifierHelper::getNewIdentifier();
        LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Generated new Identifier for %s: %s", 
                 itemTypeName.c_str(), identifier.c_str());
        
        // TODO: If identifier is empty, and generate a new one, should we write it to database?
        bool success = IdentifierHelper::writeIdentifierToDb(getItemType(), identifier);
        if (!success) {
            LOG_ERROR(LOG_TAG, "doCloneOutIdentifier - Failed to write Identifier to database for %s", 
                     itemTypeName.c_str());
            // return ErrorCode::ERROR_DATA_SERIALIZE_FAILED;
        }
    }
    
    if (!IdentifierHelper::isValidIdentifier(identifier)) {
        LOG_ERROR(LOG_TAG, "doCloneOutIdentifier - Invalid Identifier for %s: %s", 
                  itemTypeName.c_str(), identifier.c_str());
        return ErrorCode::ERROR_IDENTIFIER_INVALID;
    }
    
    std::string destPath = CloneConfig::getInstance().getDestCloneItemPath(getItemType()) + getIdentifierFileName();
    LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Writing Identifier file to: %s", destPath.c_str());
    
    ErrorCode result = IdentifierHelper::writeIdentifierFile(destPath, identifier);
    if (result != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "doCloneOutIdentifier - Failed to write Identifier file: %s", destPath.c_str());
        return result;
    }
    
    LOG_INFO(LOG_TAG, "doCloneOutIdentifier - Successfully wrote Identifier to file for %s: %s", 
             itemTypeName.c_str(), identifier.c_str());
    
    return ErrorCode::SUCCESS;
}


ErrorCode ICloneItem::doCloneOutHistory() {
    if (!hasHistorySupport()) {
        LOG_INFO(LOG_TAG, "doCloneOutHistory - History not supported for item type: %s", 
                 getItemTypeName(getItemType()).c_str());
        return ErrorCode::SUCCESS;
    }
    
    std::string historyFileName = getHistoryFileName();
    std::string destOutHistoryPath = CloneConfig::getInstance().getDestCloneItemPath(getItemType()) + "/" + historyFileName;
    std::string sourcePath;
    
    if(CloneConfig::getInstance().useXmlForHistory()) {
        sourcePath = CloneConfig::getInstance().getCloneHistoryPath() + "/" + historyFileName;
        LOG_INFO(LOG_TAG, "doCloneOutHistory - Exporting history from: %s, Item: %s",
            sourcePath.c_str(), getItemTypeName(getItemType()).c_str());
    }

    
    IHistoryManager& historyManager = HistoryManagerFactory::getInstance(
        CloneConfig::getInstance().useXmlForHistory()
    );
    
    ErrorCode result = historyManager.exportHistory(sourcePath, destOutHistoryPath, getItemType());
    if (result != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "Failed to export history for item: %s", getItemTypeName(getItemType()).c_str());
        return result;
    }
    
    LOG_INFO(LOG_TAG, "Successfully exported history to file: %s", destOutHistoryPath.c_str());
    return ErrorCode::SUCCESS;
}


ErrorCode ICloneItem::doCloneInHistory(
    CloneActionType actionType,
    const std::string& cloneSourceReason) {
    
    if (!hasHistorySupport()) {
        LOG_INFO(LOG_TAG, "doCloneInHistory - History not supported for item type: %s", 
                 getItemTypeName(getItemType()).c_str());
        return ErrorCode::SUCCESS;
    }
    
    LOG_INFO(LOG_TAG, "doCloneInHistory - Action: %s, reason: %s, item type: %s", 
             getActionTypeName(actionType).c_str(), cloneSourceReason.c_str(), 
             getItemTypeName(getItemType()).c_str());
    
    auto& historyManager = HistoryManagerFactory::getInstance(
        CloneConfig::getInstance().useXmlForHistory()
    );
    
    std::string historyFileName = getHistoryFileName();
    std::string tvHistoryPath = CloneConfig::getInstance().getCloneHistoryPath() + "/" + historyFileName;
    std::string sourceHistoryPath = CloneConfig::getInstance().getSrcCloneItemPath(getItemType()) + "/" + historyFileName;

    LOG_INFO(LOG_TAG, "Source History Path: %s", sourceHistoryPath.c_str());
    LOG_INFO(LOG_TAG, "TV History Path: %s", tvHistoryPath.c_str());
    
    ErrorCode result = historyManager.mergeHistory(
        sourceHistoryPath,
        tvHistoryPath,
        getItemType(),
        cloneSourceReason);
    
    if (result != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "doCloneInHistory - mergeHistory failed: %d", 
                  static_cast<int>(result));
    }
    
    return result;
}

ErrorCode ICloneItem::doResetIdentifier(const std::string& inIdtStr) {
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "doResetIdentifier - Item: %s, Identifier: %s", itemTypeName.c_str(), inIdtStr.c_str());
    
    if (!hasIdentifierSupport()) {
        LOG_INFO(LOG_TAG, "doResetIdentifier - Identifier not supported for item type: %s",
                 itemTypeName.c_str());
        return ErrorCode::SUCCESS;
    }
    
    // Identifier content have 3 kinds value:
    // a) Empty string "", it means the initinial value
    // b) Invalid Identifier, it means the clock is invalid 00/00/0000:--:--
    // c) Valid Identifier, it means the identifier is valid

    bool success = IdentifierHelper::writeIdentifierToDb(getItemType(), inIdtStr);
    if (!success) {
        LOG_ERROR(LOG_TAG, "Failed to reset identifier to default value for %s",
                 itemTypeName.c_str());
        return ErrorCode::ERROR_DATA_SERIALIZE_FAILED;
    }
    
    LOG_INFO(LOG_TAG, "Successfully reset identifier to default value for %s: %s",
             itemTypeName.c_str(), IdentifierHelper::IDENTIFIER_INVALID);


    // Update the last clone status of items to empty string
    IdentifierHelper::writeLastStatusToDb(getItemType(), "");
    
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::doUpdateHistory(const std::string& reason, const std::string& inTimeStr) {
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "doUpdateHistory - Item: %s, Reason: %s, Time: %s", itemTypeName.c_str(), reason.c_str(), inTimeStr.c_str());
    
    if (!hasHistorySupport()) {
        LOG_INFO(LOG_TAG, "doUpdateHistory - History not supported for item type: %s",
                 itemTypeName.c_str());
        return ErrorCode::SUCCESS;
    }
    
    auto& historyManager = HistoryManagerFactory::getInstance(
        CloneConfig::getInstance().useXmlForHistory()
    );
    
    std::string historyFileName = getHistoryFileName();
    std::string historyFilePath = CloneConfig::getInstance().getCloneHistoryPath() + "/" + historyFileName;
    
    ErrorCode clearResult = historyManager.updateCloneItemHistory(historyFilePath, getItemType(), reason, inTimeStr);
    if (clearResult != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "Failed to clear history for item: %s, error: %d",
                itemTypeName.c_str(), static_cast<int>(clearResult));
        return clearResult;
    }

    LOG_INFO(LOG_TAG, "Successfully cleared history for item: %s with reason: %s", itemTypeName.c_str(), reason.c_str());
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::clearData(const std::string& clearReason) {
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "clearData - Item: %s", itemTypeName.c_str());

    // 重置开始和结束时间为默认值（空字符串）
    m_startTime.clear();
    m_endTime.clear();
    
    // TODO:
    // 1. Each item delete its own clone data
    // 2. Then reset identifier and history
    // 3. Below is Java sample flow
    // 08-09 13:33:17.395  2333  2333 D DataCleaner: clearData /data/media/0/HTV/Clone/Clone_data/Channel_logo_default
    // 08-09 13:33:17.404  2333  2333 D DataCleaner: clearData /data/media/0/HTV/Clone/Clone_data/Channel_logo_default/highRes
    // 08-09 13:33:17.404  2333  2333 D DataCleaner: clearData /data/media/0/HTV/Clone/Clone_data/Channel_logo_custom
    // 08-09 13:33:17.408  2333  2333 D DataCleaner: clearData /data/media/0/HTV/Clone/Clone_data/Channel_logo_custom/highRes
    
    // 1. Reset Identifier to default value
    // TODO: generate new identifier or use Invalid Identifier??? 
    //       In Java code, some items use empty string, and some use new identifier
    std::string strDateTime = "";
    std::string strIdt = "";
    
    if(!isResetIdentifierAtAll()) {
        strDateTime = IdentifierHelper::getDateTimeString();
        strIdt = IdentifierHelper::getNewIdentifierWithDateTime(strDateTime);
    }

    ErrorCode result = doResetIdentifier(strIdt);
    if (result != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "Failed to reset identifier: %d", static_cast<int>(result));
        return result;
    }
    
    // 2. Update history
    result = doUpdateHistory(clearReason, strDateTime);
    if (result != ErrorCode::SUCCESS) {
        LOG_ERROR(LOG_TAG, "Failed to reset history: %d", static_cast<int>(result));
        return result;
    }
    
    LOG_INFO(LOG_TAG, "clearData completed successfully for item: %s", itemTypeName.c_str());
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::compressData(
    std::function<void(int progress)> progressCallback) {
    
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "compressData - Item: %s", itemTypeName.c_str());
    
    // 默认实现：模拟压缩进度
    // 对于大多数项目，压缩可能不是必需的
    // 如果需要特殊压缩逻辑，子类可以重载此方法
    if (progressCallback) {
        for (int i = 0; i <= 100; i += 10) {
            progressCallback(i);
        }
    }
    
    return ErrorCode::SUCCESS;
}

ErrorCode ICloneItem::preExecuteItem(
    CloneActionType actionType,
    std::function<bool()> cancelCheckCallback) {
    
    // 记录开始时间
    m_startTime = IdentifierHelper::getDateTimeString();
    
    std::string itemTypeName = getItemTypeName(getItemType());
    LOG_INFO(LOG_TAG, "preExecuteItem - Item: %s, Action: %s, StartTime: %s",
             itemTypeName.c_str(), 
             getActionTypeName(actionType).c_str(),
             m_startTime.c_str());
    
    if (cancelCheckCallback && cancelCheckCallback()) {
        return ErrorCode::ERROR_OPERATION_CANCELLED;
    }
    
    return ErrorCode::SUCCESS;
}

} // namespace CloneMgrMw

(File has 417 lines total.)

# task_progress List (Optional - Plan Mode)

While in PLAN MODE, if you've outlined concrete steps or requirements for the user, you may include a preliminary todo list using the task_progress parameter.

Reminder on how to use the task_progress parameter:


1. To create or update a todo list, include the task_progress parameter in the next tool call
2. Review each item and update its status:
   - Mark completed items with: - [x]
   - Keep incomplete items as: - [ ]
   - Add new items if you discover additional steps
3. Modify the list as needed:
		- Add any new steps you've discovered
		- Reorder if the sequence has changed
4. Ensure the list accurately reflects the current state

**Remember:** Keeping the task_progress list updated helps track progress and ensures nothing is missed.
<environment_details>
# Visual Studio Code Visible Files
src/item/firmware_item.cpp

# Visual Studio Code Open Tabs
src/item/iclone_item.h
src/item/iclone_item.cpp
src/item/firmware_item.cpp

# Current Time
4/21/2026, 10:01:16 AM (Asia/Shanghai, UTC+8:00)

# Context Window Usage
15,021 / 128K tokens used (12%)

# Current Mode
PLAN MODE
In this mode you should focus on information gathering, asking questions, and architecting a solution. Once you have a plan, use the plan_mode_respond tool to engage in a conversational back and forth with the user. Do not use the plan_mode_respond tool until you've gathered all the information you need e.g. with read_file or ask_followup_question.
(Remember: If it seems the user wants you to use tools only available in Act Mode, you should ask the user to "toggle to Act mode" (use those words) - they will have to manually do this themselves with the Plan/Act toggle button below. You do not have the ability to switch to Act Mode yourself, and must wait for the user to do it themselves once they are satisfied with the plan. You also cannot present an option to toggle to Act mode, as this will be something you need to direct the user to do manually themselves.)
</environment_details>