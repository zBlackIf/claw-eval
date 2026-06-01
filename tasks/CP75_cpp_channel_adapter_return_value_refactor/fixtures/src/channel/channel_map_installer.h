#ifndef CHANNEL_MAP_INSTALLER_H
#define CHANNEL_MAP_INSTALLER_H

#include <memory>
#include <vector>
#include <string>
#include "../include/error_code.h"
#include "../include/channel_types.h"

namespace CloneMgrMw {

class VendorChannelAdapter;

class ChannelMapInstaller {
public:
    ChannelMapInstaller(std::shared_ptr<VendorChannelAdapter> adapter);
    ~ChannelMapInstaller();

    ErrorCode installChannelMap(const std::string& mapFilePath);
    ErrorCode installSingleChannel(const BaseChannel* channel, const ChannelConfig& config);

private:
    /**
     * Convert a BaseChannel to vendor-specific VendorChannel format.
     * Currently uses output parameter pattern - needs refactoring to return value.
     */
    ErrorCode convertToVendorChannel(const BaseChannel* channel,
                                      const ChannelConfig& config,
                                      VendorChannel* outChannel);

    ErrorCode validateChannel(const VendorChannel& channel);
    ErrorCode applyChannelToDevice(const VendorChannel& channel);

    std::shared_ptr<VendorChannelAdapter> m_adapter;
    std::vector<VendorChannel> m_installedChannels;
};

} // namespace CloneMgrMw

#endif // CHANNEL_MAP_INSTALLER_H
