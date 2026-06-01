package com.zte.ums.xw.fm.service.filesync;

import lombok.extern.slf4j.Slf4j;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 同步文件名生成器。
 * 根据网元类型和请求ID生成带有时间戳和序号的文件名。
 */
@Slf4j
public class XwFileNameGenarater {

    private static final String FILE_SUFFIX = ".JSON";
    private AtomicInteger fileIndex = new AtomicInteger(0);
    private String baseName;

    public XwFileNameGenarater() {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMddHHmmss");
        this.baseName = sdf.format(new Date());
    }

    /**
     * 生成带网元类型前缀的文件名。
     * 格式: {neType}_{timestamp}_{index}_{requestId}.JSON
     *
     * @param neType 网元类型（如 gNodeB, eNodeB 等）
     * @param requestId 请求ID
     * @return 生成的文件名
     */
    public String generateFileName(String neType, String requestId) {
        int idx = fileIndex.incrementAndGet();
        return neType + "_" + baseName + "_" + idx + "_" + requestId + FILE_SUFFIX;
    }

    /**
     * 获取单文件模式下的文件名。
     */
    public String getSingleFileName() {
        return baseName + "_single" + FILE_SUFFIX;
    }
}
