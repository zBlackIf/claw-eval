#ifndef NVT_CHANNEL_ADAPTER_H
#define NVT_CHANNEL_ADAPTER_H

#include "vendor_channel_adapter.h"

namespace CloneMgrMw {

/**
 * NVT (Novatek) SoC Channel Adapter implementation.
 */
class NvtChannelAdapter : public VendorChannelAdapter {
public:
    NvtChannelAdapter();
    ~NvtChannelAdapter() override;

    ErrorCode transformChannel(VendorChannel& channel) override;
    ErrorCode validateVendorChannel(const VendorChannel& channel) override;
    ErrorCode writeChannel(const VendorChannel& channel) override;
    ErrorCode readChannel(int channelNumber, VendorChannel& outChannel) override;

private:
    void applyNvtFrequencyOffset(VendorChannel& channel);
};

} // namespace CloneMgrMw

#endif // NVT_CHANNEL_ADAPTER_H
