#include "channel_map_installer.h"
#include "../vendor/vendor_channel_adapter.h"
#include "../utils/logger.h"

#define LOG_TAG "ChannelMapInstaller"

namespace CloneMgrMw {

ChannelMapInstaller::ChannelMapInstaller(std::shared_ptr<VendorChannelAdapter> adapter)
    : m_adapter(std::move(adapter)) {}

ChannelMapInstaller::~ChannelMapInstaller() = default;

ErrorCode ChannelMapInstaller::installChannelMap(const std::string& mapFilePath) {
    // Parse channel map file
    auto channels = parseChannelMapFile(mapFilePath);
    if (channels.empty()) {
        LOG_E(LOG_TAG, "No channels found in map file: %s", mapFilePath.c_str());
        return ErrorCode::INVALID_PARAM;
    }

    for (const auto& channel : channels) {
        ChannelConfig config = getConfigForChannel(channel.get());

        // Current pattern: output parameter
        VendorChannel vendorChannel;
        ErrorCode err = convertToVendorChannel(channel.get(), config, &vendorChannel);
        if (err != ErrorCode::OK) {
            LOG_E(LOG_TAG, "Failed to convert channel %d: %d",
                  channel->getChannelNumber(), static_cast<int>(err));
            continue;
        }

        err = validateChannel(vendorChannel);
        if (err != ErrorCode::OK) {
            LOG_W(LOG_TAG, "Channel %d validation failed, skipping",
                  channel->getChannelNumber());
            continue;
        }

        err = applyChannelToDevice(vendorChannel);
        if (err != ErrorCode::OK) {
            LOG_E(LOG_TAG, "Failed to apply channel %d to device",
                  channel->getChannelNumber());
            return err;
        }

        m_installedChannels.push_back(vendorChannel);
    }

    LOG_I(LOG_TAG, "Successfully installed %zu channels", m_installedChannels.size());
    return ErrorCode::OK;
}

ErrorCode ChannelMapInstaller::installSingleChannel(const BaseChannel* channel,
                                                      const ChannelConfig& config) {
    // Another call site using output parameter pattern
    VendorChannel vendorChannel;
    ErrorCode err = convertToVendorChannel(channel, config, &vendorChannel);
    if (err != ErrorCode::OK) {
        return err;
    }

    err = validateChannel(vendorChannel);
    if (err != ErrorCode::OK) {
        return err;
    }

    return applyChannelToDevice(vendorChannel);
}

ErrorCode ChannelMapInstaller::convertToVendorChannel(const BaseChannel* channel,
                                                        const ChannelConfig& config,
                                                        VendorChannel* outChannel) {
    if (!channel || !outChannel) {
        return ErrorCode::INVALID_PARAM;
    }

    outChannel->frequency = channel->getFrequency();
    outChannel->bandwidth = config.bandwidth;
    outChannel->symbolRate = config.symbolRate;
    outChannel->modulation = config.modulation;
    outChannel->channelNumber = channel->getChannelNumber();
    outChannel->serviceName = channel->getServiceName();

    // Apply vendor-specific transformations
    ErrorCode err = m_adapter->transformChannel(*outChannel);
    if (err != ErrorCode::OK) {
        LOG_E(LOG_TAG, "Vendor transform failed for channel %d",
              channel->getChannelNumber());
        return err;
    }

    return ErrorCode::OK;
}

ErrorCode ChannelMapInstaller::validateChannel(const VendorChannel& channel) {
    if (channel.frequency == 0 || channel.bandwidth == 0) {
        return ErrorCode::INVALID_PARAM;
    }
    return m_adapter->validateVendorChannel(channel);
}

ErrorCode ChannelMapInstaller::applyChannelToDevice(const VendorChannel& channel) {
    return m_adapter->writeChannel(channel);
}

} // namespace CloneMgrMw
