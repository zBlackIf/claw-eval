package cn.iocoder.yudao.module.external.pojo.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class MesJobRecordVO {

    private Long id;

    private String jobCode;

    private String productCode;

    private String batchNo;

    private Integer printMode;

    private Integer status;

    private String operatorName;

    private LocalDateTime createTime;
}
