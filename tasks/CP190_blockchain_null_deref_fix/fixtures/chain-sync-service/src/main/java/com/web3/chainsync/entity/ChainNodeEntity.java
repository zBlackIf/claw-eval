package com.web3.chainsync.entity;

/**
 * Represents a blockchain node's metadata retrieved from the registry.
 */
public class ChainNodeEntity {
    private String nodeId;
    private String chainType;   // e.g. "ETH", "BSC", "POLYGON"
    private String rpcEndpoint;
    private int syncPriority;
    private boolean active;

    public ChainNodeEntity() {}

    public ChainNodeEntity(String nodeId, String chainType, String rpcEndpoint, int syncPriority, boolean active) {
        this.nodeId = nodeId;
        this.chainType = chainType;
        this.rpcEndpoint = rpcEndpoint;
        this.syncPriority = syncPriority;
        this.active = active;
    }

    public String getNodeId() { return nodeId; }
    public void setNodeId(String nodeId) { this.nodeId = nodeId; }

    public String getChainType() { return chainType; }
    public void setChainType(String chainType) { this.chainType = chainType; }

    public String getRpcEndpoint() { return rpcEndpoint; }
    public void setRpcEndpoint(String rpcEndpoint) { this.rpcEndpoint = rpcEndpoint; }

    public int getSyncPriority() { return syncPriority; }
    public void setSyncPriority(int syncPriority) { this.syncPriority = syncPriority; }

    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }

    @Override
    public String toString() {
        return "ChainNodeEntity{nodeId='" + nodeId + "', chainType='" + chainType +
               "', rpcEndpoint='" + rpcEndpoint + "', syncPriority=" + syncPriority +
               ", active=" + active + '}';
    }
}
