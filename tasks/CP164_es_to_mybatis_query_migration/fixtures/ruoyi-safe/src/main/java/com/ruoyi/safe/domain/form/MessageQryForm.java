package com.ruoyi.safe.domain.form;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@ApiModel(value = "消息查询表单")
@Data
public class MessageQryForm {

    @ApiModelProperty(value = "关键字搜索（标题/内容）")
    private String keyword;

    @ApiModelProperty(value = "消息类型")
    private Integer msgType;

    @ApiModelProperty(value = "已读标志")
    private Integer readFlag;
}
