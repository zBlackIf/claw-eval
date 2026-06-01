package com.ruoyi.safe.service.search;

import lombok.Data;

import java.util.Map;

/**
 * Auth filter configuration for UniversalSearchService.
 */
@Data
public class UniversalSearchAuthFilter {

    private String index;
    private Map<String, Object> filter;
}
