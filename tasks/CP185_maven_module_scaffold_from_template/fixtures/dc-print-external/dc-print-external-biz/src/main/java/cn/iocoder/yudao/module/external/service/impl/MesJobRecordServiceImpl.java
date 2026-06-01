package cn.iocoder.yudao.module.external.service.impl;

import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.module.external.domain.MesJobRecord;
import cn.iocoder.yudao.module.external.mapper.MesJobRecordMapper;
import cn.iocoder.yudao.module.external.pojo.dto.MesJobRecordSearchDTO;
import cn.iocoder.yudao.module.external.service.MesJobRecordService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class MesJobRecordServiceImpl implements MesJobRecordService {

    private final MesJobRecordMapper mesJobRecordMapper;

    @Override
    public PageResult<MesJobRecord> getPage(MesJobRecordSearchDTO searchDTO) {
        LambdaQueryWrapper<MesJobRecord> wrapper = new LambdaQueryWrapper<>();
        if (searchDTO.getJobCode() != null) {
            wrapper.like(MesJobRecord::getJobCode, searchDTO.getJobCode());
        }
        if (searchDTO.getStatus() != null) {
            wrapper.eq(MesJobRecord::getStatus, searchDTO.getStatus());
        }
        Page<MesJobRecord> page = mesJobRecordMapper.selectPage(
                new Page<>(searchDTO.getPageNo(), searchDTO.getPageSize()), wrapper);
        return new PageResult<>(page.getRecords(), page.getTotal());
    }

    @Override
    public MesJobRecord getById(Long id) {
        return mesJobRecordMapper.selectById(id);
    }

    @Override
    public void create(MesJobRecord record) {
        mesJobRecordMapper.insert(record);
    }

    @Override
    public void updateStatus(Long id, Integer status) {
        MesJobRecord record = new MesJobRecord();
        record.setId(id);
        record.setStatus(status);
        mesJobRecordMapper.updateById(record);
    }
}
