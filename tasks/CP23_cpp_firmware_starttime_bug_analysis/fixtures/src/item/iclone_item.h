#pragma once
#include <string>
#include <memory>
#include "../helper/identifier_helper.h"

enum class ItemStatus {
    IDLE,
    PREPARING,
    EXECUTING,
    COMPLETED,
    FAILED
};

class ICloneItem {
public:
    ICloneItem() = default;
    virtual ~ICloneItem() = default;

    virtual bool preExecuteItem();
    virtual bool executeItem() = 0;
    virtual void postExecuteItem();
    virtual void onError(const std::string& error);

    std::string getStartTime() const { return m_startTime; }
    std::string getEndTime() const { return m_endTime; }
    ItemStatus getStatus() const { return m_status; }
    std::string getItemId() const { return m_itemId; }

protected:
    std::string m_itemId;
    std::string m_startTime;
    std::string m_endTime;
    ItemStatus m_status = ItemStatus::IDLE;
    std::string m_errorMsg;
};
