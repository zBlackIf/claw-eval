package com.ruoyi.safe.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

@ApiModel(value = "消息VO")
@Data
public class MessageVO implements Serializable {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty(value = "ID")
    private Long id;

    @ApiModelProperty(value = "标题")
    private String title;

    @ApiModelProperty(value = "内容")
    private String content;

    @ApiModelProperty(value = "消息类型")
    private Integer msgType;

    @ApiModelProperty(value = "发送人姓名")
    private String senderName;

    @ApiModelProperty(value = "已读标志")
    private Integer readFlag;

    @ApiModelProperty(value = "创建时间")
    private Date createTime;
}
