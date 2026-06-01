-- ============================================================================
-- HOF-SCM 基础数据模块 DDL (PostgreSQL)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 9.6 产品信息子表 (Product Table)
-- 说明: 产品加工参数表（standard_sku维度）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS base_data.product (
    id                BIGSERIAL    PRIMARY KEY,               -- 产品ID，自增主键
    standard_sku      VARCHAR(50)  UNIQUE NOT NULL,            -- 产品SKU，工厂识别的单品货号
    image_url         VARCHAR(500),                            -- 缩略图链接
    category_id       BIGINT,                                  -- 产品类目ID，关联【产品类目表】
    product_name      VARCHAR(200) NOT NULL,                   -- 产品名称/单品描述
    -- 核心工艺
    product_size      VARCHAR(100),                            -- 尺寸，物理规格
    spec_code         VARCHAR(50),                             -- 规格编码，面料/材料代码
    spec_description  TEXT,                                    -- 规格描述，面料及基本工艺详述
    -- 工艺细节（对应类目定义的标签1~5）
    process_value_1   VARCHAR(200),                            -- 工艺细节1内容，对应类目定义的标签1
    process_value_2   VARCHAR(200),                            -- 工艺细节2内容，对应类目定义的标签2
    process_value_3   VARCHAR(200),                            -- 工艺细节3内容，对应类目定义的标签3
    process_value_4   VARCHAR(200),                            -- 工艺细节4内容，对应类目定义的标签4
    process_value_5   VARCHAR(200),                            -- 工艺细节5内容，对应类目定义的标签5
    -- 系统字段
    status            SMALLINT     DEFAULT 0,                  -- 状态：0-草稿, 1-激活
    created_by        VARCHAR(100),
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_by        VARCHAR(100),
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    deleted           SMALLINT     DEFAULT 0
);
COMMENT ON TABLE  base_data.product IS '9.6 产品信息子表 - 产品加工参数表';
COMMENT ON COLUMN base_data.product.process_value_1 IS '工艺细节1内容，对应类目定义的标签1';
COMMENT ON COLUMN base_data.product.process_value_2 IS '工艺细节2内容，对应类目定义的标签2';
COMMENT ON COLUMN base_data.product.process_value_3 IS '工艺细节3内容，对应类目定义的标签3';
COMMENT ON COLUMN base_data.product.process_value_4 IS '工艺细节4内容，对应类目定义的标签4';
COMMENT ON COLUMN base_data.product.process_value_5 IS '工艺细节5内容，对应类目定义的标签5';

-- ---------------------------------------------------------------------------
-- 9.10 供应商-辅料供应策略配置表 (Supplier Accessory Policy)
-- 说明: 针对特定工厂的策略锁定，实现"一厂一策"
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS base_data.supplier_accessory_policy (
    id                  BIGSERIAL    PRIMARY KEY,
    supplier_id         BIGINT       NOT NULL,                  -- 供应商ID，关联供应商信息表
    accessory_category  VARCHAR(50)  NOT NULL,                  -- 辅料品类
    sourcing_type       VARCHAR(50)  NOT NULL,                  -- 供应方式：客供/工料/工料（需额外结算）
    created_by          VARCHAR(100),
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_by          VARCHAR(100),
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    deleted             SMALLINT     DEFAULT 0
);
COMMENT ON TABLE base_data.supplier_accessory_policy IS '9.10 供应商-辅料供应策略配置表';
