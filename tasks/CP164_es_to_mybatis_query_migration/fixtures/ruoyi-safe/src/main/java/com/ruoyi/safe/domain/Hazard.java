package com.ruoyi.safe.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.ruoyi.common.core.domain.BaseEntity;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

@ApiModel(value = "隐患")
@Data
@EqualsAndHashCode(callSuper = true)
@Accessors(chain = true)
@TableName("sh_hazard")
public class Hazard extends BaseEntity {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty(value = "ID")
    @TableId(type = IdType.AUTO)
    private Long id;

    @ApiModelProperty(value = "隐患编号")
    private String hazardNo;

    @ApiModelProperty(value = "隐患描述")
    private String description;

    @ApiModelProperty(value = "隐患等级 1-一般 2-重大")
    private Integer hazardLevel;

    @ApiModelProperty(value = "隐患类型")
    private String hazardType;

    @ApiModelProperty(value = "隐患状态 0-待整改 1-整改中 2-待验收 3-已闭环")
    private Integer status;

    @ApiModelProperty(value = "发现人ID")
    private Long discoverId;

    @ApiModelProperty(value = "发现人姓名")
    private String discoverName;

    @ApiModelProperty(value = "责任人ID")
    private Long responsibleId;

    @ApiModelProperty(value = "责任人姓名")
    private String responsibleName;

    @ApiModelProperty(value = "所属部门ID")
    private Long deptId;

    @ApiModelProperty(value = "所属部门名称")
    private String deptName;

    @ApiModelProperty(value = "发现地点")
    private String location;

    @ApiModelProperty(value = "整改期限")
    private String deadline;

    @ApiModelProperty(value = "删除标志 0-未删除 1-已删除")
    private Integer delFlag;
}
