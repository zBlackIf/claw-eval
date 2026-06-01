package com.hof.basedata.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 9.6 产品信息子表
 * 产品加工参数表（standard_sku维度）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("base_data.product")
public class Product implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 产品ID，自增主键
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    // ========== 核心编码 ==========

    /**
     * 产品SKU，工厂识别的单品货号 [主键]
     */
    private String standardSku;

    /**
     * 缩略图链接
     */
    private String imageUrl;

    /**
     * 产品类目ID，关联【产品类目表】，决定工艺细节的显示标签
     */
    private Long categoryId;

    /**
     * 产品名称/单品描述
     */
    private String productName;

    // ========== 核心工艺 ==========

    /**
     * 尺寸，物理规格
     */
    private String productSize;

    /**
     * 规格编码，面料/材料代码
     */
    private String specCode;

    /**
     * 规格描述，面料及基本工艺详述
     */
    private String specDescription;

    // ========== 工艺细节（对应类目定义的标签1~5） ==========

    /**
     * 工艺细节1内容，对应类目定义的标签1
     */
    private String processValue1;

    /**
     * 工艺细节2内容，对应类目定义的标签2
     */
    private String processValue2;

    /**
     * 工艺细节3内容，对应类目定义的标签3
     */
    private String processValue3;

    /**
     * 工艺细节4内容，对应类目定义的标签4
     */
    private String processValue4;

    /**
     * 工艺细节5内容，对应类目定义的标签5
     */
    private String processValue5;

    // ========== 系统字段 ==========

    /**
     * 状态：0-草稿, 1-激活
     */
    private Integer status;

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
