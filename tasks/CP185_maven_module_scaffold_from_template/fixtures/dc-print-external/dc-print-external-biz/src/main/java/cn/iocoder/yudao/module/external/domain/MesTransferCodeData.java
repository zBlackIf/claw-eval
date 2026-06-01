package cn.iocoder.yudao.module.external.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * MES 传输码数据
 */
@Data
@TableName("mes_transfer_code_data")
public class MesTransferCodeData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String transferCode;

    private String productCode;

    private String batchNo;

    private String codeContent;

    private Integer codeType;

    private Integer status;

    private LocalDateTime createTime;
}
