package com.web3.chainsync.entity;

/**
 * Cached RPC routing info from the chain registry service.
 */
public class RpcRouteInfo {
    private String chainType;
    private int result;  // 1 = success, 0 = not found
    private String preferredEndpoint;

    public RpcRouteInfo() {}

    public RpcRouteInfo(String chainType, int result, String preferredEndpoint) {
        this.chainType = chainType;
        this.result = result;
        this.preferredEndpoint = preferredEndpoint;
    }

    public String getChainType() { return chainType; }
    public void setChainType(String chainType) { this.chainType = chainType; }

    public int getResult() { return result; }
    public void setResult(int result) { this.result = result; }

    public String getPreferredEndpoint() { return preferredEndpoint; }
    public void setPreferredEndpoint(String preferredEndpoint) { this.preferredEndpoint = preferredEndpoint; }
}
