package com.hof.basedata.service.impl;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.hof.basedata.dto.AccessoryPolicyQueryDTO;
import com.hof.basedata.dto.AccessoryPolicyResponseDTO;
import com.hof.basedata.entity.AccessoryPolicy;
import com.hof.basedata.mapper.AccessoryPolicyMapper;
import com.hof.basedata.service.AccessoryPolicyService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Service implementation for AccessoryPolicy management
 *
 * @author HOF SCM
 * @since 1.0.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AccessoryPolicyServiceImpl extends ServiceImpl<AccessoryPolicyMapper, AccessoryPolicy>
        implements AccessoryPolicyService {

    private final AccessoryPolicyMapper accessoryPolicyMapper;

    @Override
    public IPage<AccessoryPolicyResponseDTO> query(AccessoryPolicyQueryDTO queryDTO) {
        Page<AccessoryPolicy> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        return accessoryPolicyMapper.selectPageWithFilters(page, queryDTO);
    }

    @Override
    public List<AccessoryPolicyResponseDTO> getBySupplierId(Long supplierId) {
        return accessoryPolicyMapper.selectBySupplierId(supplierId);
    }

    @Override
    public List<AccessoryPolicyResponseDTO> getByStandardSku(String standardSku) {
        return accessoryPolicyMapper.selectByStandardSku(standardSku);
    }

    @Override
    public List<AccessoryPolicyResponseDTO> getBySkuAndSupplier(String standardSku, Long supplierId) {
        return accessoryPolicyMapper.selectBySkuAndSupplier(standardSku, supplierId);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public AccessoryPolicyResponseDTO create(AccessoryPolicyCreateDTO createDTO) {
        log.info("Creating accessory policy for supplier ID: {}", createDTO.getSupplierId());
        AccessoryPolicy policy = new AccessoryPolicy();
        policy.setSupplierId(createDTO.getSupplierId());
        policy.setAccessoryCategory(createDTO.getAccessoryCategory());
        policy.setSourcingType(createDTO.getSourcingType());
        save(policy);

        AccessoryPolicyResponseDTO response = new AccessoryPolicyResponseDTO();
        response.setId(policy.getId());
        response.setSupplierId(policy.getSupplierId());
        response.setAccessoryCategory(policy.getAccessoryCategory());
        response.setSourcingType(policy.getSourcingType());
        return response;
    }
}
