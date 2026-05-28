#ifndef VENDOR_CHANNEL_ADAPTER_H
#define VENDOR_CHANNEL_ADAPTER_H

#include "../include/error_code.h"
#include "../include/channel_types.h"

namespace CloneMgrMw {

/**
 * Abstract base class for vendor-specific channel adapters.
 * Subclasses implement SoC-specific channel operations.
 */
class VendorChannelAdapter {
public:
    virtual ~VendorChannelAdapter() = default;

    virtual ErrorCode transformChannel(VendorChannel& channel) = 0;
    virtual ErrorCode validateVendorChannel(const VendorChannel& channel) = 0;
    virtual ErrorCode writeChannel(const VendorChannel& channel) = 0;
    virtual ErrorCode readChannel(int channelNumber, VendorChannel& outChannel) = 0;

    // TODO: Add addDirectTuneChannel interface here
};

} // namespace CloneMgrMw

#endif // VENDOR_CHANNEL_ADAPTER_H
