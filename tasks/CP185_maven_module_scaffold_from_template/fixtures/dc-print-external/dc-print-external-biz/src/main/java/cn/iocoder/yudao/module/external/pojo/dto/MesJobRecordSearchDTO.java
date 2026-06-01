package cn.iocoder.yudao.module.external.pojo.dto;

import lombok.Data;

@Data
public class MesJobRecordSearchDTO {

    private String jobCode;

    private String productCode;

    private Integer status;

    private Integer pageNo = 1;

    private Integer pageSize = 10;
}
