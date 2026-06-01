package org.jeecg.modules.mobileHospital.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface InstrumentPanelArchive1Mapper {

    @Select("SELECT count(0) FROM t_instrument_panel_archive")
    int countArchiveRecords();
}
