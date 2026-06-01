package com.zte.ums.xw.fm.model;

import lombok.Data;

/**
 * VAS 网元信息查询结果。
 * result == 1 表示查询成功，nbiType 有效。
 */
@Data
public class VasRmUidInfo {
    private int result;
    private String nbiType;
    private String ruid;
}
