package com.ruoyi.safe.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.safe.domain.Hazard;
import com.ruoyi.safe.domain.form.HazardQryForm;
import com.ruoyi.safe.domain.vo.HazardVO;

public interface IHazardService extends IService<Hazard> {

    IPage<HazardVO> queryPage(HazardQryForm form, int pageNum, int pageSize);

    HazardVO getDetailById(Long id);
}
