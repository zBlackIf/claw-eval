package com.web3.chainsync.service;

/**
 * Request object for block sync file query operations.
 */
public class BlockSyncRequest {
    private String nodeIdentifier;
    private long startBlock;
    private long endBlock;
    private String requestId;

    public BlockSyncRequest() {}

    public BlockSyncRequest(String nodeIdentifier, long startBlock, long endBlock) {
        this.nodeIdentifier = nodeIdentifier;
        this.startBlock = startBlock;
        this.endBlock = endBlock;
    }

    public String getNodeIdentifier() { return nodeIdentifier; }
    public void setNodeIdentifier(String nodeIdentifier) { this.nodeIdentifier = nodeIdentifier; }

    public long getStartBlock() { return startBlock; }
    public void setStartBlock(long startBlock) { this.startBlock = startBlock; }

    public long getEndBlock() { return endBlock; }
    public void setEndBlock(long endBlock) { this.endBlock = endBlock; }

    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
}
