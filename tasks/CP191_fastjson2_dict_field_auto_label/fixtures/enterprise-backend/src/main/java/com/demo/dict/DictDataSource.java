package com.demo.dict;

import java.util.Map;

/**
 * 模拟字典数据源
 *
 * 当前系统字典值:
 *   user_status: 0=禁用, 1=启用
 *   gender: 0=未知, 1=男, 2=女
 *   yes_no: 0=否, 1=是
 *   priority: 1=低, 2=中, 3=高, 4=紧急
 */
public class DictDataSource {

    private static final Map<String, Map<String, String>> DICT_MAP = Map.of(
        "user_status", Map.of("0", "禁用", "1", "启用"),
        "gender", Map.of("0", "未知", "1", "男", "2", "女"),
        "yes_no", Map.of("0", "否", "1", "是"),
        "priority", Map.of("1", "低", "2", "中", "3", "高", "4", "紧急")
    );

    /**
     * 根据字典类型和值获取标签
     */
    public static String getLabel(String dictType, String dictValue) {
        Map<String, String> typeMap = DICT_MAP.get(dictType);
        if (typeMap == null) return null;
        return typeMap.get(dictValue);
    }
}
