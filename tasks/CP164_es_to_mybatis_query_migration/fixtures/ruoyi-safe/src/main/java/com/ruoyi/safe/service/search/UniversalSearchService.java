package com.ruoyi.safe.service.search;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * Universal search service backed by Elasticsearch.
 * This service provides full-text search and complex query capabilities
 * via ES indices that mirror the database tables.
 *
 * NOTE: For environments with < 10k records and < 10 concurrent users,
 * this ES dependency is overkill and should be replaced with direct
 * MyBatis-Plus database queries.
 */
@Service
public class UniversalSearchService {

    /**
     * Search with pagination using ES index.
     */
    public <T> IPage<T> searchPage(Page<T> page, UniversalSearchAuthFilter authFilter, Class<T> clazz) {
        // ES-backed search implementation
        throw new UnsupportedOperationException("ES service not available in this environment");
    }

    /**
     * Count documents matching filter in the specified ES index.
     */
    public Long count(String index, Map<String, Object> filter) {
        // ES-backed count implementation
        throw new UnsupportedOperationException("ES service not available in this environment");
    }
}
