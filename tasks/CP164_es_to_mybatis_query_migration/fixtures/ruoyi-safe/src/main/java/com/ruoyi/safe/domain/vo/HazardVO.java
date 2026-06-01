package com.ruoyi.safe.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

@ApiModel(value = "隐患VO")
@Data
public class HazardVO implements Serializable {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty(value = "ID")
    private Long id;

    @ApiModelProperty(value = "隐患编号")
    private String hazardNo;

    @ApiModelProperty(value = "隐患描述")
    private String description;

    @ApiModelProperty(value = "隐患等级")
    private Integer hazardLevel;

    @ApiModelProperty(value = "隐患类型")
    private String hazardType;

    @ApiModelProperty(value = "隐患状态")
    private Integer status;

    @ApiModelProperty(value = "发现人姓名")
    private String discoverName;

    @ApiModelProperty(value = "责任人姓名")
    private String responsibleName;

    @ApiModelProperty(value = "所属部门名称")
    private String deptName;

    @ApiModelProperty(value = "发现地点")
    private String location;

    @ApiModelProperty(value = "整改期限")
    private String deadline;

    @ApiModelProperty(value = "创建时间")
    private Date createTime;
}
