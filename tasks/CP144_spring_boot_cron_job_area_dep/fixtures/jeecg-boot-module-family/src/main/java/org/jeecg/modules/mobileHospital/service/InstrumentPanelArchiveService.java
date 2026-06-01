package org.jeecg.modules.mobileHospital.service;

public interface InstrumentPanelArchiveService {

    /**
     * 清空归档表
     */
    void truncateArchiveTable();

    /**
     * 执行数据归档
     * @return 归档记录数
     */
    int archiveData();
}
