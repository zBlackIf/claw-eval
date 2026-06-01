package com.ruoyi.safe.domain.form;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@ApiModel(value = "隐患查询表单")
@Data
public class HazardQryForm {

    @ApiModelProperty(value = "关键字搜索（编号/描述/地点）")
    private String keyword;

    @ApiModelProperty(value = "隐患等级")
    private Integer hazardLevel;

    @ApiModelProperty(value = "隐患状态")
    private Integer status;

    @ApiModelProperty(value = "隐患类型")
    private String hazardType;

    @ApiModelProperty(value = "责任人ID")
    private Long responsibleId;

    @ApiModelProperty(value = "所属部门ID")
    private Long deptId;
}
