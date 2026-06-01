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

@ApiModel(value = "用户消息")
@Data
@EqualsAndHashCode(callSuper = true)
@Accessors(chain = true)
@TableName("sh_message_user")
public class MessageUser extends BaseEntity {

    private static final long serialVersionUID = 1L;

    public static final Integer READ_FLAG_UN_READ = 0;
    public static final Integer READ_FLAG_READ = 1;

    @ApiModelProperty(value = "ID")
    @TableId(type = IdType.AUTO)
    private Long id;

    @ApiModelProperty(value = "消息ID")
    private Long messageId;

    @ApiModelProperty(value = "用户ID")
    private Long userId;

    @ApiModelProperty(value = "已读标志 0-未读 1-已读")
    private Integer readFlag;

    @ApiModelProperty(value = "删除标志 0-未删除 1-已删除")
    private Integer delFlag;
}
