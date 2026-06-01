package com.hof.basedata.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 9.10 供应商-辅料供应策略配置表
 * 针对特定工厂的策略锁定，实现"一厂一策"
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("base_data.supplier_accessory_policy")
public class AccessoryPolicy implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 供应商ID，关联【供应商信息表】，确定是哪家工厂
     */
    private Long supplierId;

    /**
     * 辅料品类，关联配件表中的 accessory_type，按大类锁定
     */
    private String accessoryCategory;

    /**
     * 供应方式：客供 / 工料 / 工料（需额外结算）[核心]
     * 优先级高于配件表默认值
     */
    private String sourcingType;

    // ========== 系统字段 ==========

    @TableField("created_by")
    private String createdBy;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField("updated_by")
    private String updatedBy;

    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
