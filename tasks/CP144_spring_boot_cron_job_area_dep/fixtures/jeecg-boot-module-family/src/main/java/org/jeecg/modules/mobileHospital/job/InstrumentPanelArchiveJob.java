package org.jeecg.modules.mobileHospital.job;

import lombok.extern.slf4j.Slf4j;
import org.jeecg.modules.mobileHospital.service.InstrumentPanelArchiveService;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 仪表盘数据归档定时任务
 * Cron: 每天凌晨2点执行 (0 0 2 * * ?)
 */
@Slf4j
@Component
public class InstrumentPanelArchiveJob implements Job {

    @Autowired
    private InstrumentPanelArchiveService instrumentPanelArchiveService;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        log.info("=== InstrumentPanelArchiveJob 开始执行 ===");
        long startTime = System.currentTimeMillis();
        try {
            // Step 1: 清空归档表
            instrumentPanelArchiveService.truncateArchiveTable();
            log.info("归档表清空完成");

            // Step 2: 执行数据归档
            int count = instrumentPanelArchiveService.archiveData();
            log.info("数据归档完成，共归档 {} 条记录", count);

            long elapsed = System.currentTimeMillis() - startTime;
            log.info("=== InstrumentPanelArchiveJob 执行完成，耗时 {} ms ===", elapsed);
        } catch (Exception e) {
            log.error("InstrumentPanelArchiveJob 执行失败: {}", e.getMessage(), e);
            throw new JobExecutionException("定时任务执行失败", e);
        }
    }
}
