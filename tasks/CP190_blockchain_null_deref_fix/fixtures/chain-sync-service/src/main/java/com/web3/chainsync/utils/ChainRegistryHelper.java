package com.web3.chainsync.utils;

import com.web3.chainsync.entity.ChainNodeEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Helper for querying chain node registry (DB-backed).
 */
public class ChainRegistryHelper {

    private static final Logger log = LoggerFactory.getLogger(ChainRegistryHelper.class);

    /**
     * Queries the registry for a chain node by its unique identifier.
     * Returns null if not found or on DB errors.
     */
    public static ChainNodeEntity getNodeByIdentifier(String nodeIdentifier) {
        ChainNodeEntity entity = null;
        try {
            // Simulates DB query — in production queries chain_node_registry table
            String querySql = "SELECT * FROM chain_node_registry WHERE node_id = ?";
            log.info("CHAIN_SYNC: getNodeByIdentifier, nodeId={}, sql={}", nodeIdentifier, querySql);

            // DB operation would populate entity here
            // entity = jdbcTemplate.queryForObject(...);

            log.info("CHAIN_SYNC: getNodeByIdentifier, result={}", entity);
        } catch (Exception e) {
            log.error("CHAIN_SYNC: getNodeByIdentifier error, nodeId: {}", nodeIdentifier, e);
        }
        return entity;
    }

    /**
     * Queries the registry for the default RPC endpoint for a given chain type.
     * Returns null if no default is configured.
     */
    public static String getDefaultRpcEndpoint(String chainType) {
        try {
            // Would query: SELECT rpc_endpoint FROM chain_defaults WHERE chain_type = ?
            log.info("CHAIN_SYNC: getDefaultRpcEndpoint for chainType={}", chainType);
            return null;  // placeholder
        } catch (Exception e) {
            log.error("CHAIN_SYNC: getDefaultRpcEndpoint error: {}", e.getMessage(), e);
            return null;
        }
    }
}
