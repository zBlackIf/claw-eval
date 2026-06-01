package com.hof.basedata.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hof.basedata.dto.AccessoryPolicyQueryDTO;
import com.hof.basedata.dto.AccessoryPolicyResponseDTO;
import com.hof.basedata.entity.AccessoryPolicy;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * Mapper interface for AccessoryPolicy entity
 *
 * @author HOF SCM
 * @since 1.0.0
 */
@Mapper
public interface AccessoryPolicyMapper extends BaseMapper<AccessoryPolicy> {

    /**
     * Query accessory policies with filters and pagination
     *
     * @param page pagination object
     * @param query query filters
     * @return paginated accessory policy list
     */
    IPage<AccessoryPolicyResponseDTO> selectPageWithFilters(Page<AccessoryPolicy> page, @Param("query") AccessoryPolicyQueryDTO query);

    /**
     * Get accessory policies by standard SKU
     *
     * @param standardSku standard SKU
     * @return list of accessory policies
     */
    List<AccessoryPolicyResponseDTO> selectByStandardSku(@Param("standardSku") String standardSku);

    /**
     * Get accessory policies by supplier ID
     *
     * @param supplierId supplier ID
     * @return list of accessory policies
     */
    List<AccessoryPolicyResponseDTO> selectBySupplierId(@Param("supplierId") Long supplierId);

    /**
     * Get accessory policies by SKU and supplier
     *
     * @param standardSku standard SKU
     * @param supplierId supplier ID
     * @return list of accessory policies
     */
    List<AccessoryPolicyResponseDTO> selectBySkuAndSupplier(@Param("standardSku") String standardSku, @Param("supplierId") Long supplierId);
}
