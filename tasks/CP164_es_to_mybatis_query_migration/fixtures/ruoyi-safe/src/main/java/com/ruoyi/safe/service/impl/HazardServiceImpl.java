package com.ruoyi.safe.service.impl;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ruoyi.common.core.service.BaseServiceImpl;
import com.ruoyi.safe.domain.Hazard;
import com.ruoyi.safe.domain.form.HazardQryForm;
import com.ruoyi.safe.domain.vo.HazardVO;
import com.ruoyi.safe.mapper.HazardMapper;
import com.ruoyi.safe.service.IHazardService;
import com.ruoyi.safe.service.search.UniversalSearchService;
import com.ruoyi.safe.service.search.UniversalSearchAuthFilter;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class HazardServiceImpl extends BaseServiceImpl<HazardMapper, Hazard> implements IHazardService {

    @Autowired
    private UniversalSearchService universalSearchService;

    @Override
    public IPage<HazardVO> queryPage(HazardQryForm form, int pageNum, int pageSize) {
        Map<String, Object> filter = buildQueryFilter(form);
        UniversalSearchAuthFilter authFilter = new UniversalSearchAuthFilter();
        authFilter.setIndex("sh_hazard");
        authFilter.setFilter(filter);
        return universalSearchService.searchPage(new Page<>(pageNum, pageSize), authFilter, Hazard.class)
                .convert(this::convertToVO);
    }

    @Override
    public HazardVO getDetailById(Long id) {
        Hazard po = getById(id);
        if (po == null) {
            return null;
        }
        return convertToVO(po);
    }

    private Map<String, Object> buildQueryFilter(HazardQryForm form) {
        Map<String, Object> filter = new HashMap<>();
        if (form.getHazardLevel() != null) {
            filter.put("hazardLevel", form.getHazardLevel());
        }
        if (form.getStatus() != null) {
            filter.put("status", form.getStatus());
        }
        if (StrUtil.isNotBlank(form.getHazardType())) {
            filter.put("hazardType", form.getHazardType());
        }
        if (form.getResponsibleId() != null) {
            filter.put("responsibleId", form.getResponsibleId());
        }
        if (form.getDeptId() != null) {
            filter.put("deptId", form.getDeptId());
        }
        if (StrUtil.isNotBlank(form.getKeyword())) {
            filter.put("keyword", form.getKeyword());
            filter.put("keyword_fields", "hazardNo,description,location");
        }
        filter.put("delFlag", 0);
        return filter;
    }

    private HazardVO convertToVO(Hazard po) {
        HazardVO vo = new HazardVO();
        BeanUtils.copyProperties(po, vo);
        return vo;
    }
}
