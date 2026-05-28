#include "nvt_channel_adapter.h"
#include "../utils/logger.h"

#define LOG_TAG "NvtChannelAdapter"

namespace CloneMgrMw {

NvtChannelAdapter::NvtChannelAdapter() = default;
NvtChannelAdapter::~NvtChannelAdapter() = default;

ErrorCode NvtChannelAdapter::transformChannel(VendorChannel& channel) {
    applyNvtFrequencyOffset(channel);
    channel.vendorData["nvt_tuner_mode"] = "auto";
    return ErrorCode::OK;
}

ErrorCode NvtChannelAdapter::validateVendorChannel(const VendorChannel& channel) {
    if (channel.frequency < 48000 || channel.frequency > 862000) {
        LOG_E(LOG_TAG, "Frequency %d out of NVT range", channel.frequency);
        return ErrorCode::OUT_OF_RANGE;
    }
    return ErrorCode::OK;
}

ErrorCode NvtChannelAdapter::writeChannel(const VendorChannel& channel) {
    LOG_I(LOG_TAG, "Writing channel %d to NVT tuner", channel.channelNumber);
    // NVT-specific channel write implementation
    return ErrorCode::OK;
}

ErrorCode NvtChannelAdapter::readChannel(int channelNumber, VendorChannel& outChannel) {
    LOG_I(LOG_TAG, "Reading channel %d from NVT tuner", channelNumber);
    // NVT-specific channel read implementation
    return ErrorCode::OK;
}

void NvtChannelAdapter::applyNvtFrequencyOffset(VendorChannel& channel) {
    // NVT tuners need a small frequency offset for optimal reception
    channel.frequency += 125;
}

} // namespace CloneMgrMw
