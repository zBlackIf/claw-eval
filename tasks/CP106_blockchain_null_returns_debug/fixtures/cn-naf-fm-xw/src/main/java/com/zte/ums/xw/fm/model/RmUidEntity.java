package com.zte.ums.xw.fm.model;

import lombok.Data;

/**
 * 网元资源实体，对应 cmcc_cm_rmuid 表。
 */
@Data
public class RmUidEntity {
    private String rmuid;
    private String nafnetype;
    private String rmid;
    private String neName;
    private String subnetId;
}
