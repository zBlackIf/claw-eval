#include "channel_map_builder.h"
#include "../utils/logger.h"

#define LOG_TAG "ChannelMapBuilder"

namespace CloneMgrMw {

/**
 * Reference implementation: returns result through return value using unique_ptr.
 * This is the pattern that ChannelMapInstaller::convertToVendorChannel should follow.
 */
std::unique_ptr<BaseChannel> ChannelMapBuilder::convertVendorChannelToBaseChannel(
    const VendorChannel& vendorChannel, const ChannelConfig& config) {

    auto baseChannel = std::make_unique<BaseChannel>();
    baseChannel->setFrequency(vendorChannel.frequency);
    baseChannel->setChannelNumber(vendorChannel.channelNumber);
    baseChannel->setServiceName(vendorChannel.serviceName);
    baseChannel->setBandwidth(config.bandwidth);

    // Apply reverse transformation
    if (!baseChannel->isValid()) {
        LOG_E(LOG_TAG, "Converted channel is invalid");
        return nullptr;  // Error indicated by null return
    }

    return baseChannel;
}

} // namespace CloneMgrMw
