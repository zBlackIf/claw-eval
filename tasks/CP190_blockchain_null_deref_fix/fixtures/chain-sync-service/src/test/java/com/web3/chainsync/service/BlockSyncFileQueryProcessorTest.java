package com.web3.chainsync.service;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Existing tests for BlockSyncFileQueryProcessor.
 * Tests basic construction and request object.
 */
class BlockSyncFileQueryProcessorTest {

    @Test
    void testBlockSyncRequestCreation() {
        BlockSyncRequest request = new BlockSyncRequest("node-eth-001", 18000000L, 18001000L);
        assertEquals("node-eth-001", request.getNodeIdentifier());
        assertEquals(18000000L, request.getStartBlock());
        assertEquals(18001000L, request.getEndBlock());
    }

    @Test
    void testBlockSyncRequestSetters() {
        BlockSyncRequest request = new BlockSyncRequest();
        request.setNodeIdentifier("node-bsc-002");
        request.setStartBlock(30000000L);
        request.setEndBlock(30001000L);
        request.setRequestId("req-abc-123");
        assertEquals("node-bsc-002", request.getNodeIdentifier());
        assertEquals("req-abc-123", request.getRequestId());
    }
}
