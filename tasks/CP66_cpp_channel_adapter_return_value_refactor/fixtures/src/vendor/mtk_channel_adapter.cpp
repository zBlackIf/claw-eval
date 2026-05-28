#include "mtk_channel_adapter.h"
#include "../utils/logger.h"

#define LOG_TAG "MtkChannelAdapter"

namespace CloneMgrMw {

MtkChannelAdapter::MtkChannelAdapter() = default;
MtkChannelAdapter::~MtkChannelAdapter() = default;

ErrorCode MtkChannelAdapter::transformChannel(VendorChannel& channel) {
    applyMtkModulationMapping(channel);
    return ErrorCode::OK;
}

ErrorCode MtkChannelAdapter::validateVendorChannel(const VendorChannel& channel) {
    if (channel.symbolRate == 0) {
        LOG_E(LOG_TAG, "Symbol rate cannot be zero for MTK");
        return ErrorCode::INVALID_PARAM;
    }
    return ErrorCode::OK;
}

ErrorCode MtkChannelAdapter::writeChannel(const VendorChannel& channel) {
    LOG_I(LOG_TAG, "Writing channel %d to MTK tuner", channel.channelNumber);
    return ErrorCode::OK;
}

ErrorCode MtkChannelAdapter::readChannel(int channelNumber, VendorChannel& outChannel) {
    LOG_I(LOG_TAG, "Reading channel %d from MTK tuner", channelNumber);
    return ErrorCode::OK;
}

void MtkChannelAdapter::applyMtkModulationMapping(VendorChannel& channel) {
    // MTK uses different modulation enum values
    if (channel.modulation == 3) {  // QAM256
        channel.vendorData["mtk_mod"] = "8";
    } else if (channel.modulation == 2) {  // QAM128
        channel.vendorData["mtk_mod"] = "7";
    }
}

} // namespace CloneMgrMw
