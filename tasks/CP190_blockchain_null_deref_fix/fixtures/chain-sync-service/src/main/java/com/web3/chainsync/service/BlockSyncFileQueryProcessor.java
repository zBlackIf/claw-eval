package com.web3.chainsync.service;

import com.web3.chainsync.entity.ChainNodeEntity;
import com.web3.chainsync.entity.RpcRouteInfo;
import com.web3.chainsync.utils.ChainRegistryHelper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Processes block sync file queries for a given chain node.
 * Retrieves block data files from remote RPC nodes and stores locally.
 */
public class BlockSyncFileQueryProcessor {

    private static final Logger log = LoggerFactory.getLogger(BlockSyncFileQueryProcessor.class);

    private final IRpcRoutingService rpcRoutingService;
    private final List<String> allOutputFiles = new ArrayList<>();

    public BlockSyncFileQueryProcessor(IRpcRoutingService rpcRoutingService) {
        this.rpcRoutingService = rpcRoutingService;
    }

    /**
     * Main entry point: sync block data files for the given node.
     */
    public void processBlockSyncQuery(BlockSyncRequest syncRequest) {
        long startTime = System.currentTimeMillis();
        String nodeIdentifier = syncRequest.getNodeIdentifier();
        log.info("CHAIN_SYNC: Starting block sync for node={}", nodeIdentifier);

        String chainType = getChainType(nodeIdentifier);
        String remoteDir = getRemoteStoragePath(chainType);
        log.info("CHAIN_SYNC: remoteDir={}", remoteDir);

        allOutputFiles.clear();
        List<String> resultFiles = downloadBlockFiles(syncRequest, nodeIdentifier, chainType);
        log.info("CHAIN_SYNC: resultFiles={}", resultFiles);

        for (String localFilePath : resultFiles) {
            File localFile = new File(localFilePath);
            String fileName = localFile.getName();
            String targetPath = remoteDir + "/" + fileName;
            log.info("CHAIN_SYNC: uploading {} to {}", fileName, targetPath);

            boolean uploaded = uploadToStorage(localFilePath, targetPath);
            if (uploaded) {
                allOutputFiles.add(targetPath);
            }
            // cleanup temp file
            localFile.delete();
        }
        log.info("CHAIN_SYNC: BlockSyncFileQueryProcessor useTime:{}", (System.currentTimeMillis() - startTime));
    }

    /**
     * Determines the chain type for a given node identifier.
     * First checks the RPC routing cache, falls back to registry DB lookup.
     *
     * BUG: Line 68 — ChainRegistryHelper.getNodeByIdentifier() can return null
     * when the node is not found in registry, causing NPE on .getChainType().
     */
    private String getChainType(String nodeIdentifier) {
        String chainType;
        rpcRoutingService.refreshRouting(nodeIdentifier);
        RpcRouteInfo routeInfo = rpcRoutingService.getCachedRouteInfo();
        if (routeInfo != null && routeInfo.getResult() == 1) {
            chainType = routeInfo.getChainType();
        } else {
            ChainNodeEntity nodeEntity = ChainRegistryHelper.getNodeByIdentifier(nodeIdentifier);
            chainType = nodeEntity.getChainType();  // <-- NPE here if nodeEntity is null
        }
        return chainType;
    }

    /**
     * Constructs the remote storage path for block data based on chain type.
     */
    private String getRemoteStoragePath(String chainType) {
        StringBuilder path = new StringBuilder("/data/blocks/");
        path.append(chainType);
        path.append("/sync");
        return path.toString();
    }

    /**
     * Downloads block files from the remote node.
     * Returns list of local temp file paths.
     */
    private List<String> downloadBlockFiles(BlockSyncRequest request, String nodeId, String chainType) {
        List<String> files = new ArrayList<>();
        log.info("CHAIN_SYNC: downloading blocks for node={}, chain={}, range={}-{}",
                nodeId, chainType, request.getStartBlock(), request.getEndBlock());
        // In production: connects to RPC node, downloads block data files
        return files;
    }

    /**
     * Uploads a file to distributed storage.
     */
    private boolean uploadToStorage(String localPath, String remotePath) {
        try {
            log.info("CHAIN_SYNC: uploading file {} -> {}", localPath, remotePath);
            // In production: uploads to S3/IPFS/distributed storage
            return true;
        } catch (Exception e) {
            log.error("CHAIN_SYNC: upload failed for {}: {}", localPath, e.getMessage(), e);
            return false;
        }
    }

    public List<String> getAllOutputFiles() {
        return allOutputFiles;
    }
}
