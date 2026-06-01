package com.hof.basedata.dto;

import lombok.Data;

/**
 * Query DTO for AccessoryPolicy search/filter
 */
@Data
public class AccessoryPolicyQueryDTO {

    /**
     * 供应商ID筛选
     */
    private Long supplierId;

    /**
     * 辅料品类筛选
     */
    private String accessoryCategory;

    /**
     * 供应方式筛选
     */
    private String sourcingType;

    /**
     * 产品SKU筛选
     */
    private String standardSku;

    /**
     * 页码
     */
    private Integer pageNum = 1;

    /**
     * 每页数量
     */
    private Integer pageSize = 10;
}
