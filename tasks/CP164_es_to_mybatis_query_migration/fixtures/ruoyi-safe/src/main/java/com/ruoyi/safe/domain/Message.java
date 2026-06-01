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

@ApiModel(value = "消息")
@Data
@EqualsAndHashCode(callSuper = true)
@Accessors(chain = true)
@TableName("sh_message")
public class Message extends BaseEntity {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty(value = "ID")
    @TableId(type = IdType.AUTO)
    private Long id;

    @ApiModelProperty(value = "标题")
    private String title;

    @ApiModelProperty(value = "内容")
    private String content;

    @ApiModelProperty(value = "消息类型 1-系统通知 2-任务通知 3-审批通知")
    private Integer msgType;

    @ApiModelProperty(value = "关联业务ID")
    private Long bizId;

    @ApiModelProperty(value = "关联业务类型")
    private String bizType;

    @ApiModelProperty(value = "发送人ID")
    private Long senderId;

    @ApiModelProperty(value = "发送人姓名")
    private String senderName;

    @ApiModelProperty(value = "删除标志 0-未删除 1-已删除")
    private Integer delFlag;
}
