package com.baosight.egdw.jh.sm.service;

import com.baosight.iplat4j.core.ei.EiInfo;
import com.baosight.iplat4j.core.service.impl.ServiceBase;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * ServiceJHSM3110 - Service for 主原料明细成本标准
 *
 * Handles CRUD operations for the SA_JH00_WA0001 table.
 * The grid displays costCenter as "CODE-DESCRIPTION" (e.g., "1234-炼钢厂")
 * and wce as "CODE-DESCRIPTION" (e.g., "41001-铁合金").
 * stNo is also displayed as "CODE-DESCRIPTION" format.
 *
 * BUG: When saving (insert/update), the full "CODE-DESCRIPTION" string
 * is passed directly to the SQL statement, but the DB columns have strict
 * length limits (COST_CENTER=4, WCE=5, ST_NO portion=8).
 * This causes DB2 SQLCODE=-302 (SQLSTATE=22001) on insert/update.
 */
public class ServiceJHSM3110 extends ServiceBase {

    public EiInfo initLoad(EiInfo inInfo) {
        return query(inInfo);
    }

    public EiInfo query(EiInfo inInfo) {
        // Uses JHSM3110.query - joins with description tables
        // Returns costCenter as "CODE-DESC", wce as "CODE-DESC", stNo as "CODE-DESC"
        inInfo.setBlock("result",
            dao.query("JHSM3110.query", inInfo.getAttr()));
        return inInfo;
    }

    public EiInfo insert(EiInfo inInfo) {
        List<Map<String, Object>> rows = inInfo.getBlock("result").getRows();
        for (Map<String, Object> row : rows) {
            row.put("recId", UUID.randomUUID().toString().replace("-", ""));
            // BUG: costCenter, wce, stNo contain "CODE-DESCRIPTION" from the grid
            // but DB columns are too narrow for the full string
            dao.insert("JHSM3110.insert", row);
        }
        return inInfo;
    }

    public EiInfo update(EiInfo inInfo) {
        List<Map<String, Object>> rows = inInfo.getBlock("result").getRows();
        for (Map<String, Object> row : rows) {
            // BUG: same issue - costCenter/wce/stNo have "CODE-DESCRIPTION"
            dao.update("JHSM3110.update", row);
        }
        return inInfo;
    }

    public EiInfo delete(EiInfo inInfo) {
        List<Map<String, Object>> rows = inInfo.getBlock("result").getRows();
        for (Map<String, Object> row : rows) {
            dao.delete("JHSM3110.delete", row);
        }
        return inInfo;
    }
}
