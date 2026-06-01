package cn.iocoder.yudao.module.external.service;

import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.module.external.domain.MesJobRecord;
import cn.iocoder.yudao.module.external.pojo.dto.MesJobRecordSearchDTO;

public interface MesJobRecordService {

    PageResult<MesJobRecord> getPage(MesJobRecordSearchDTO searchDTO);

    MesJobRecord getById(Long id);

    void create(MesJobRecord record);

    void updateStatus(Long id, Integer status);
}
