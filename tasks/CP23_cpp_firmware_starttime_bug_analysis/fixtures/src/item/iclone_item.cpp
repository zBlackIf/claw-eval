#include "iclone_item.h"
#include "../helper/identifier_helper.h"

bool ICloneItem::preExecuteItem() {
    m_status = ItemStatus::PREPARING;
    m_startTime = IdentifierHelper::getDateTimeString();
    m_errorMsg.clear();
    return true;
}

void ICloneItem::postExecuteItem() {
    m_endTime = IdentifierHelper::getDateTimeString();
    m_status = ItemStatus::COMPLETED;
}

void ICloneItem::onError(const std::string& error) {
    m_errorMsg = error;
    m_status = ItemStatus::FAILED;
    m_endTime = IdentifierHelper::getDateTimeString();
}
