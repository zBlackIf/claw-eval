package com.zte.ums.xw.fm.utils.db;

import com.zte.ums.xw.fm.model.RmUidEntity;
import com.zte.ums.xw.fm.model.QueryCondition;
import com.zte.ums.xw.fm.utils.PathSafeUtil;
import lombok.extern.slf4j.Slf4j;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.function.Consumer;

/**
 * 告警数据库操作助手类。
 * 提供告警相关的数据库查询操作，包括网元信息查询、告警数据检索等。
 */
@Slf4j
public class AlarmDbHelper {

    /**
     * 根据 RUID 查询网元实体信息。
     * 从 cmcc_cm_rmuid 或其副本表中查询对应网元的 nafnetype。
     *
     * @param ruid 网元资源唯一标识
     * @return 查询到的网元实体，查询无结果或异常时返回 null
     */
    public static RmUidEntity getRmUidEntityByRuid(String ruid) {
        RmUidEntity rmUidEntity = null;
        try {
            String baseSql = "select distinct nafnetype from cmcc_cm_rmuid where rmuid=?";
            EpcCmService epcCmService = ServiceLocatorHolder.getLocator().getService(EpcCmService.class);
            boolean isCopy = epcCmService.isPmValueCopyTable();
            String tableName = isCopy ? "cmcc_cm_rmuid_copy" : "cmcc_cm_rmuid";
            String querySql = PathSafeUtil.escapePath(baseSql.replace("cmcc_cm_rmuid", tableName));
            log.info("XW_NAF_FM: getRmUidEntityByRuid, ruid={}, querySql={}", ruid, querySql);

            rmUidEntity = DatabaseAccess.querySingle(querySql, new Object[]{ruid}, rs -> {
                RmUidEntity entity = new RmUidEntity();
                entity.setNafnetype(rs.getString("nafnetype"));
                entity.setRmuid(ruid);
                return entity;
            });
            log.info("XW_NAF_FM: getRmUidEntityByRuid, result={}", rmUidEntity);
        } catch (Exception e) {
            log.error("XW_NAF_FM: getRmUidEntityByRuid error, ruid: {}", ruid, e);
        }
        return rmUidEntity;
    }

    /**
     * 根据 RUID 查询网元 RmId。
     * 用于获取网元在资源管理系统中的内部 ID。
     *
     * @param ruid 网元资源唯一标识
     * @return 网元 RmId，查询失败返回 null
     */
    public static String getRmIdByRuid(String ruid) {
        String rmId = null;
        try {
            String sql = "select rmid from cmcc_cm_rmuid where rmuid=?";
            rmId = DatabaseAccess.queryScalar(sql, new Object[]{ruid});
            log.info("XW_NAF_FM: getRmIdByRuid, ruid={}, rmId={}", ruid, rmId);
        } catch (Exception e) {
            log.error("XW_NAF_FM: getRmIdByRuid error, ruid: {}", ruid, e);
        }
        return rmId;
    }

    /**
     * 执行查询并对结果集逐行回调。
     */
    public static void executeQuery(String sql, Object[] params, Consumer<ResultSet> callback) {
        try {
            DatabaseAccess.executeWithCallback(sql, params, callback);
        } catch (Exception e) {
            log.error("XW_NAF_FM: executeQuery error, sql: {}", sql, e);
        }
    }

    private static void fillParameters(Object[] paras, PreparedStatement preparedStatement) throws SQLException {
        if (null != paras) {
            int index = 1;
            for (Object para : paras) {
                preparedStatement.setObject(index, para);
                index++;
            }
        }
    }

    private synchronized static void visitRows(IResultSetRowCallBack callBack, ResultSet result)
            throws SQLException {
        boolean isMatchData = false;
        while (result.next()) {
            if (!isMatchData) {
                isMatchData = true;
            }
            callBack.callBack(result);
        }
        if (!isMatchData) {
            throw new RuntimeException("no match data");
        }
    }
}
