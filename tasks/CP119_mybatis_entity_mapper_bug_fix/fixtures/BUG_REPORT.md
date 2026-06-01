# Bug 报告 - HOF-SCM 基础数据模块

## Bug 1: 新建产品保存报错

**现象**: 新建产品时保存失败

**错误日志**:
```
Caused by: org.postgresql.util.PSQLException: ERROR: column "process_value1" of relation "product" does not exist
Position: 119
```

**复现路径**: 后台管理 → 产品管理 → 新建产品 → 填写工艺细节 → 保存

---

## Bug 2: 辅料策略查询报错

**现象**: 辅料策略列表页加载时报错

**错误日志**:
```
org.apache.ibatis.binding.BindingException: Invalid bound statement (not found): com.hof.basedata.mapper.AccessoryPolicyMapper.selectPageWithFilters
```

**复现路径**: 后台管理 → 辅料策略 → 进入列表页

---

## 技术栈
- Java 17 + Spring Boot 3.2
- MyBatis-Plus 3.5.5
- PostgreSQL 16
- 项目结构: `hof-base-data/src/main/...`
