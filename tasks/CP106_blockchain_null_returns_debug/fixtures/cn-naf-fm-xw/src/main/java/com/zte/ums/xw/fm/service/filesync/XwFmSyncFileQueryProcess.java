package com.zte.ums.xw.fm.service.filesync;

import com.zte.ums.xw.fm.model.FmSyncFileRequest;
import com.zte.ums.xw.fm.model.QueryCondition;
import com.zte.ums.xw.fm.model.RmUidEntity;
import com.zte.ums.xw.fm.model.VasRmUidInfo;
import com.zte.ums.xw.fm.service.IVasNafService;
import com.zte.ums.xw.fm.service.IXwCommonService;
import com.zte.ums.xw.fm.service.IXwNrmService;
import com.zte.ums.xw.fm.utils.CoverityUtil;
import com.zte.ums.xw.fm.utils.db.AlarmDbHelper;
import com.zte.ums.xw.fm.constants.XwFmConst;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.io.FileUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * 区块链网元文件同步查询处理器。
 * 负责从网元节点收集告警数据文件，压缩后上传至分布式存储(S3)。
 * 文件路径基于网元类型(neType)构建，用于链上数据存证。
 */
@Slf4j
@Service
public class XwFmSyncFileQueryProcess {

    @Autowired
    private IVasNafService iVasNafService;

    @Autowired
    private IXwCommonService iXwCommonService;

    @Autowired
    private IXwNrmService xwNrmService;

    @Autowired
    private QueryConditionCreator queryConditionCreator;

    private XwFileNameGenarater xwFileNameGenarater;
    private JsonHelper jsonHelper = new JsonHelper();
    private boolean isSingleFile;
    private String moreOneFilePath;
    private String singleFilePath;
    private int byteCounts;
    private List<String> allOutputFiles = new ArrayList<>();

    /**
     * 执行文件同步查询主流程。
     * 1. 确定网元类型
     * 2. 构造远端存储路径
     * 3. 生成同步文件
     * 4. 压缩上传至S3
     */
    public void process(FmSyncFileRequest fmSyncFileRequest) {
        long startTime = System.currentTimeMillis();
        String neType;
        String neRuid = fmSyncFileRequest.getRuid();
        String omcRuid = xwNrmService.generateOmcRuid();
        log.info("XW_NAF_FM:omcRuid={}", omcRuid);
        if (neRuid.equals(omcRuid)) {
            neType = "OMC";
        } else {
            neType = getNeType(neRuid);
        }
        String remoteDir = getRemoteDir(neType);
        log.info("XW_NAF_FM:remoteDir={}", remoteDir);
        neRuid = CoverityUtil.getLeaglPath(neRuid);
        allOutputFiles.clear();
        List<String> resultFiles = createUpSynFile(fmSyncFileRequest, neRuid, neType);
        log.info("XW_NAF_FM:resultFiles={}", resultFiles);
        for (String localFilePath : resultFiles) {
            File localFile = new File(localFilePath);
            String zipFileName = localFile.getName().replaceFirst("\\.JSON\\.zip", ".zip");
            String remotePath = remoteDir + zipFileName;
            try {
                iXwCommonService.uploadFile(remotePath, localFilePath);
                log.info("XW_NAF_FM:s3 uploadFile, localFilePath={}, remotePath={}", localFilePath, remotePath);
            } catch (Exception e) {
                log.error(e.getMessage(), e);
            }
            FileUtils.deleteQuietly(new File(localFilePath));
        }
        log.info("XW_NAF_FM:AlmSyncFileQueryProcess useTime:{}", (System.currentTimeMillis() - startTime));
    }

    private String getNeType(String neRuid) {
        String neType;
        iVasNafService.checkRmUID(neRuid);
        VasRmUidInfo vasRmUidInfo = iVasNafService.getVasRmUidInfo();
        if (vasRmUidInfo != null && vasRmUidInfo.getResult() == 1) {
            neType = vasRmUidInfo.getNbiType();
        } else {
            RmUidEntity rmUidEntityByRuid = AlarmDbHelper.getRmUidEntityByRuid(neRuid);
            neType = rmUidEntityByRuid.getNafnetype();
        }
        return neType;
    }

    private String getRemoteDir(String neType) {
        StringBuilder remoteDir = new StringBuilder("/HX/ZC");

        remoteDir.append(File.separator)
                .append(iXwCommonService.getOmcCode())
                .append(File.separator)
                .append(neType)
                .append(File.separator)
                .append(XwFmConst.FM)
                .append(File.separator);

        SimpleDateFormat dateformat = new SimpleDateFormat("yyyyMMdd");
        String dateDir = dateformat.format(new Date());

        remoteDir.append(dateDir)
                .append(File.separator);

        return remoteDir.toString();
    }

    private List<String> createUpSynFile(FmSyncFileRequest fmSyncFileRequest, String neRuid, String neType) {
        isSingleFile = true;
        xwFileNameGenarater = new XwFileNameGenarater();
        QueryCondition condition = queryConditionCreator.getCondition(fmSyncFileRequest, neRuid);
        moreOneFilePath = getNeRmId(neRuid) + "-" + xwFileNameGenarater.generateFileName(neType, fmSyncFileRequest.getRequestId());
        singleFilePath = checkInFilePath(getNeRmId(neRuid) + "-" + xwFileNameGenarater.getSingleFileName());
        byteCounts = 0;
        AlarmDbHelper.executeQuery(condition.getSql(), condition.getParas(), resultSet
                -> writeAlarmSyncFile(fmSyncFileRequest.getRequestId(), neRuid, neType, resultSet));
        jsonHelper.endTxt();
        zipAndSaveFile();
        return allOutputFiles;
    }

    private void writeAlarmSyncFile(String requestId, String neRuid, String neType, Object resultSet) {
        // Simplified: writes alarm data to JSON file
        log.info("XW_NAF_FM: writing alarm sync file for requestId={}, neRuid={}", requestId, neRuid);
    }

    private String getNeRmId(String neRuid) {
        return neRuid.replaceAll("[^a-zA-Z0-9]", "_");
    }

    private String checkInFilePath(String path) {
        return "/tmp/fm_sync/" + path;
    }

    private void zipAndSaveFile() {
        if (singleFilePath != null) {
            allOutputFiles.add(singleFilePath + ".JSON.zip");
        }
    }
}
