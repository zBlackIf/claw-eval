package com.hof.basedata.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Response DTO for AccessoryPolicy
 */
@Data
public class AccessoryPolicyResponseDTO {

    private Long id;

    /**
     * 供应商ID
     */
    private Long supplierId;

    /**
     * 辅料品类
     */
    private String accessoryCategory;

    /**
     * 供应方式
     */
    private String sourcingType;

    /**
     * 创建人
     */
    private String createdBy;

    /**
     * 创建时间
     */
    private LocalDateTime createdAt;

    /**
     * 更新人
     */
    private String updatedBy;

    /**
     * 更新时间
     */
    private LocalDateTime updatedAt;
}
