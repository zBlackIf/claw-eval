package com.web3.chainsync.service;

import com.web3.chainsync.entity.RpcRouteInfo;

/**
 * Interface for the RPC routing cache service.
 */
public interface IRpcRoutingService {

    /**
     * Refresh routing info for a specific node.
     */
    void refreshRouting(String nodeIdentifier);

    /**
     * Get cached routing info. May return null if cache miss.
     */
    RpcRouteInfo getCachedRouteInfo();
}
