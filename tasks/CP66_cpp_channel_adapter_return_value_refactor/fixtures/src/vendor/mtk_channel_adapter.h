#ifndef MTK_CHANNEL_ADAPTER_H
#define MTK_CHANNEL_ADAPTER_H

#include "vendor_channel_adapter.h"

namespace CloneMgrMw {

/**
 * MTK (MediaTek) SoC Channel Adapter implementation.
 */
class MtkChannelAdapter : public VendorChannelAdapter {
public:
    MtkChannelAdapter();
    ~MtkChannelAdapter() override;

    ErrorCode transformChannel(VendorChannel& channel) override;
    ErrorCode validateVendorChannel(const VendorChannel& channel) override;
    ErrorCode writeChannel(const VendorChannel& channel) override;
    ErrorCode readChannel(int channelNumber, VendorChannel& outChannel) override;

private:
    void applyMtkModulationMapping(VendorChannel& channel);
};

} // namespace CloneMgrMw

#endif // MTK_CHANNEL_ADAPTER_H
