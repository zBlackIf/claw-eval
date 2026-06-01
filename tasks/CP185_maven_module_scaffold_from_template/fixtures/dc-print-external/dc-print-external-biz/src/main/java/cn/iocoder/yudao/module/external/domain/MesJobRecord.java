package cn.iocoder.yudao.module.external.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * MES 作业记录
 */
@Data
@TableName("mes_job_record")
public class MesJobRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String jobCode;

    private String productCode;

    private String batchNo;

    private Integer printMode;

    private Integer status;

    private String operatorName;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
