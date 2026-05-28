#ifndef ICLONE_ITEM_H
#define ICLONE_ITEM_H

#include "clone_types.h"
#include "error_code.h"
#include <string>
#include <functional>
#include <vector>

namespace CloneMgrMw {

class ICloneItem {
public:
    virtual ~ICloneItem() = default;
    
    virtual CloneItemType getItemType() const = 0;
    
    virtual ErrorCode preExecuteItem(
        CloneActionType actionType,
        std::function<bool()> cancelCheckCallback);
    
    virtual ErrorCode doCloneIn(
        CloneActionType actionType,
        std::function<void(int progress)> progressCallback,
        std::function<bool()> cancelCheckCallback) = 0;
    
    virtual ErrorCode doCloneOut(
        CloneActionType actionType,
        std::function<void(int progress)> progressCallback,
        std::function<bool()> cancelCheckCallback) = 0;
    
    virtual ErrorCode postExecuteItem(
        CloneActionType actionType,
        std::function<bool()> cancelCheckCallback);
    
    virtual ErrorCode finishItem(CloneActionType actionType, CloneStatus cloneStatus);
    
    virtual ErrorCode compressData(
        std::function<void(int progress)> progressCallback);
    
    virtual bool shouldCompress(CloneActionType actionType) const = 0;
    
    /**
     * @brief 清除数据（默认实现：重置 Identifier 和 History）
     * @return 错误码
     * @note 子类可以覆盖此方法以提供特殊实现
     */
    virtual ErrorCode clearData(const std::string& clearReason);
    
    virtual bool isDataAvailable(CloneActionType actionType) const = 0;
    
    // History 相关方法
    
    /**
     * @brief 处理 Clone Out 时的 History 操作（公共实现）
     * @return 错误码
     */
    ErrorCode doCloneOutHistory();
    
    /**
     * @brief 处理 Clone In 时的 History 操作（公共实现）
     * @param actionType Clone 操作类型
     * @param cloneSourceReason Clone 源原因（可选）
     * @return 错误码
     */
    ErrorCode doCloneInHistory(
        CloneActionType actionType,
        const std::string& cloneSourceReason = "");
    
    /**
     * @brief 处理 Clone In 时的 Identifier 操作（公共实现）
     * @param actionType Clone 操作类型
     * @return 错误码
     */
    ErrorCode doCloneInIdentifier(CloneActionType actionType);
    
    /**
     * @brief 处理 Clone Out 时的 Identifier 操作（公共实现）
     * @return 错误码
     */
    ErrorCode doCloneOutIdentifier();
    
    /**
     * @brief 重置 Identifier 为默认值
     * @return 错误码
     */
    ErrorCode doResetIdentifier(const std::string& inIdtStr);
    
    /**
     * @brief Add one history record/node
     * @param reason 重置原因
     * @return 错误码
     */
    ErrorCode doUpdateHistory(const std::string& reason, const std::string& inIdtStr);
    
    // ====================================================================
    // 子类必须实现的配置函数
    // ====================================================================
    
    /**
     * @brief 获取 History 文件名（不带路径）
     * @return History 文件名，如 "TVSettings_History.xml"
     */
    virtual std::string getHistoryFileName() const = 0;
    
    /**
     * @brief 获取 Identifier 文件名（不带路径）
     * @return Identifier 文件名，如 "TVSettings_Identifier.txt"
     */
    virtual std::string getIdentifierFileName() const = 0;
    
    /**
     * @brief 获取需要拷贝的文件列表（用于 postExecuteItem）
     * @return 文件列表，如 {"file1.json", "folder/"}
     */
    virtual const std::vector<std::string>& getFilesToCopy() const = 0;
    
    // ====================================================================
    // 子类可选覆盖的函数
    // ====================================================================
    
    /**
     * @brief 检查是否支持 History 功能
     * @return true 支持 History，false 不支持
     */
    virtual bool hasHistorySupport() const { return true; }
    
    /**
     * @brief 检查是否支持 Identifier 功能
     * @return true 支持 Identifier，false 不支持
     */
    virtual bool hasIdentifierSupport() const { return true; }


    virtual bool isResetIdentifierAtAll() const { return true; }
    
    // ====================================================================
    // 时间相关方法
    // ====================================================================
    
    /**
     * @brief 获取 Item Clone 开始时间
     * @return 开始时间字符串
     */
    const std::string& getStartTime() const { return m_startTime; }
    
    /**
     * @brief 获取 Item Clone 结束时间
     * @return 结束时间字符串
     */
    const std::string& getEndTime() const { return m_endTime; }
    
    // ====================================================================
    // 辅助函数
    // ====================================================================
    
    /**
     * 检查是否是 USB Clone In 操作
     */
    static bool isUsbCloneIn(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_USB_TO_TV;
    }
    
    /**
     * 检查是否是 USB Clone Out 操作
     */
    static bool isUsbCloneOut(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_TV_TO_USB;
    }
    
    /**
     * 检查是否是 IP Clone In 操作
     */
    static bool isIPCloneIn(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_IP_TO_TV;
    }

    /**
     * 检查是否是 USB Clone Out 操作
     */
    static bool isIPCloneOut(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_TV_TO_IP;
    }

    /**
     * 检查是否是 IP Clone 操作
     */
    static bool isIPClone(CloneActionType actionType) {
        return isIPCloneIn(actionType) || isIPCloneOut(actionType);
    }
    
    /**
     * 检查是否是 USB Clone 操作
     */
    static bool isUsbClone(CloneActionType actionType) {
        return isUsbCloneIn(actionType) || isUsbCloneOut(actionType);
    }
    
    /**
     * 检查是否是 Clone In 操作
     */
    static bool isCloneIn(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_USB_TO_TV ||
               actionType == CloneActionType::ACTION_IP_TO_TV;
    }
    
    /**
     * 检查是否是 Clone Out 操作
     */
    static bool isCloneOut(CloneActionType actionType) {
        return actionType == CloneActionType::ACTION_TV_TO_USB ||
               actionType == CloneActionType::ACTION_TV_TO_IP;
    }
    
    /**
     * 根据 ActionType 获取 CloneType
     */
    static CloneType getCloneTypeFromAction(CloneActionType actionType) {
        if (isCloneIn(actionType)) {
            return CloneType::CLONE_TYPE_IN;
        } else if (isCloneOut(actionType)) {
            return CloneType::CLONE_TYPE_OUT;
        }
        // 默认返回 IN
        return CloneType::CLONE_TYPE_IN;
    }

private:
    std::string m_startTime;  // Item clone start time
    std::string m_endTime;    // Item clone end time
};

}

#endif

(File has 235 lines total.)

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
4/21/2026, 10:00:53 AM (Asia/Shanghai, UTC+8:00)

# Context Window Usage
11,673 / 128K tokens used (9%)

# Current Mode
PLAN MODE
In this mode you should focus on information gathering, asking questions, and architecting a solution. Once you have a plan, use the plan_mode_respond tool to engage in a conversational back and forth with the user. Do not use the plan_mode_respond tool until you've gathered all the information you need e.g. with read_file or ask_followup_question.
(Remember: If it seems the user wants you to use tools only available in Act Mode, you should ask the user to "toggle to Act mode" (use those words) - they will have to manually do this themselves with the Plan/Act toggle button below. You do not have the ability to switch to Act Mode yourself, and must wait for the user to do it themselves once they are satisfied with the plan. You also cannot present an option to toggle to Act mode, as this will be something you need to direct the user to do manually themselves.)
</environment_details>