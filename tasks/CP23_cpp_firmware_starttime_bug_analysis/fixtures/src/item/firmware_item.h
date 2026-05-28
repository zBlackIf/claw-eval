#ifndef FIRMWARE_ITEM_H
#define FIRMWARE_ITEM_H

#include "iclone_item.h"
#include <string>
#include <functional>

namespace CloneMgrMw {

class FirmwareItem : public ICloneItem {
public:
    FirmwareItem();
    ~FirmwareItem() override;
    
    CloneItemType getItemType() const override;
    
    ErrorCode preExecuteItem(
        CloneActionType actionType,
        std::function<bool()> cancelCheckCallback) override;
    
    ErrorCode doCloneIn(
        CloneActionType actionType,
        std::function<void(int progress)> progressCallback,
        std::function<bool()> cancelCheckCallback) override;
    
    ErrorCode doCloneOut(
        CloneActionType actionType,
        std::function<void(int progress)> progressCallback,
        std::function<bool()> cancelCheckCallback) override;
    
    bool shouldCompress(CloneActionType actionType) const override;
    bool isDataAvailable(CloneActionType actionType) const override;

    ErrorCode clearData(const std::string& clearReason) override;

    /**
     * 在指定目录中查找固件文件
     */
    std::string findFirmwareInDirectory(const std::string& directoryPath) const;
    
    
    std::string getHistoryFileName() const override;
    std::string getIdentifierFileName() const override;
    
    bool hasHistorySupport() const override;
    bool hasIdentifierSupport() const override;
    
    const std::vector<std::string>& getFilesToCopy() const override;
    
    ErrorCode finishItem(CloneActionType actionType, CloneStatus cloneStatus) override;

private:
    std::string m_firmwarePath;  // 存储找到的固件文件路径
};

}

#endif

(File has 58 lines total.)

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
4/21/2026, 9:59:37 AM (Asia/Shanghai, UTC+8:00)

# Context Window Usage
10,581 / 128K tokens used (8%)

# Current Mode
PLAN MODE
In this mode you should focus on information gathering, asking questions, and architecting a solution. Once you have a plan, use the plan_mode_respond tool to engage in a conversational back and forth with the user. Do not use the plan_mode_respond tool until you've gathered all the information you need e.g. with read_file or ask_followup_question.
(Remember: If it seems the user wants you to use tools only available in Act Mode, you should ask the user to "toggle to Act mode" (use those words) - they will have to manually do this themselves with the Plan/Act toggle button below. You do not have the ability to switch to Act Mode yourself, and must wait for the user to do it themselves once they are satisfied with the plan. You also cannot present an option to toggle to Act mode, as this will be something you need to direct the user to do manually themselves.)
</environment_details>