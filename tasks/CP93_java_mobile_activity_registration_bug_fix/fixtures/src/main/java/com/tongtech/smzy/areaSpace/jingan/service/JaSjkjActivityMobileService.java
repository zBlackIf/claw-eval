package com.tongtech.smzy.areaSpace.jingan.service;

import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityDto;
import java.util.List;

public interface JaSjkjActivityMobileService {

    List<JaSjkjActivityDto> selectActivityList(JaSjkjActivityDto dto);

    int register(JaSjkjActivityDto dto);
}
