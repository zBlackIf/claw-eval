#ifndef UPG_UPGRADE_INTERFACE_H
#define UPG_UPGRADE_INTERFACE_H

#include "../include/error_code.h"
#include <string>
#include <atomic>
#include <mutex>
#include <condition_variable>

namespace CloneMgrMw {

/**
 * UPG固件升级接口
 * 
 * @note
 * - 负责与底层系统固件升级接口对接
 * - 提供固件验证和升级功能
 * - startUpgrade方法现在是异步调用
 */
class UpgUpgradeInterface {
public:
    static UpgUpgradeInterface& getInstance();
    
    /**
     * 启动固件升级
     * 
     * @param firmwarePath 固件文件路径
     * @return SUCCESS 表示升级启动成功，其他值表示错误
     * 
     * @note
     * - 此方法是异步调用，立即返回
     * - 升级过程在后台线程中执行
     * - 调用前应确保固件文件存在且已通过验证
     */
    ErrorCode startUpgrade(const std::string& firmwarePath);
    
    /**
     * 取消升级
     * 
     * @note
     * - 如果升级正在进行中，尝试取消操作
     * - 具体取消行为取决于底层实现
     */
    void cancelUpgrade();
    
    /**
     * 验证固件文件
     * 
     * @param firmwarePath 固件文件路径
     * @return SUCCESS 表示固件有效，其他值表示错误
     * 
     * @note
     * - 验证固件文件的完整性、格式和兼容性
     * - 此方法是同步调用，立即返回结果
     * - 验证成功后会生成固件版本信息，可通过 getFirmwareVersion() 获取
     */
    ErrorCode verifyFirmware(const std::string& firmwarePath);
    
    /**
     * 获取最后一次验证的固件版本信息
     * 
     * @return 固件版本字符串，如果没有验证过或验证失败则返回空字符串
     * 
     * @note
     * - 必须在调用 verifyFirmware 成功后调用此方法
     * - verifyFirmware 的实现（通过TTUI API）会生成版本信息
     * - 版本信息格式由TTUI API决定（如 "V1.2.3"）
     */
    std::string getFirmwareVersion() const;

private:
    UpgUpgradeInterface();
    ~UpgUpgradeInterface() = default;
    UpgUpgradeInterface(const UpgUpgradeInterface&) = delete;
    UpgUpgradeInterface& operator=(const UpgUpgradeInterface&) = delete;
    
    /**
     * 模拟升级线程函数
     * @param firmwarePath 固件文件路径
     */
    void simulateUpgradeThread(const std::string& firmwarePath);
    
    // 存储版本信息，将由TTUI API在 verifyFirmware 中填充
    std::string m_lastFirmwareVersion;
    
    // 线程管理变量
    std::atomic<bool> m_isUpgrading;
    std::atomic<bool> m_upgradeCancelled;
};

} // namespace CloneMgrMw

#endif // UPG_UPGRADE_INTERFACE_H

(File has 93 lines total.)


				# TODO LIST UPDATE REQUIRED - You MUST include the task_progress parameter in your NEXT tool call.

				**Current Progress: 1/3 items completed (33%)**

				- [x] Analyze the issue with m_startTime setting in FirmwareItem
- [ ] Implement the fix by moving m_startTime assignment to the beginning of preExecuteItem
- [ ] Verify the fix is correct

				

				
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

				

**Note:** 33% of items are complete.

				
<environment_details>
# Visual Studio Code Visible Files
src/core/upg_upgrade_interface.h

# Visual Studio Code Open Tabs
src/item/iclone_item.h
src/item/iclone_item.cpp
src/item/firmware_item.cpp
src/core/upg_upgrade_interface.h

# Current Time
4/21/2026, 10:52:41 AM (Asia/Shanghai, UTC+8:00)

# Context Window Usage
25,455 / 128K tokens used (20%)

# Current Mode
PLAN MODE
In this mode you should focus on information gathering, asking questions, and architecting a solution. Once you have a plan, use the plan_mode_respond tool to engage in a conversational back and forth with the user. Do not use the plan_mode_respond tool until you've gathered all the information you need e.g. with read_file or ask_followup_question.
(Remember: If it seems the user wants you to use tools only available in Act Mode, you should ask the user to "toggle to Act mode" (use those words) - they will have to manually do this themselves with the Plan/Act toggle button below. You do not have the ability to switch to Act Mode yourself, and must wait for the user to do it themselves once they are satisfied with the plan. You also cannot present an option to toggle to Act mode, as this will be something you need to direct the user to do manually themselves.)
</environment_details>