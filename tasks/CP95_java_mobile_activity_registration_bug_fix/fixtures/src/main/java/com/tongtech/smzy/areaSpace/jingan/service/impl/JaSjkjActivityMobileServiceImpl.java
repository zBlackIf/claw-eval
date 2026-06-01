package com.tongtech.smzy.areaSpace.jingan.service.impl;

import com.tongtech.smzy.areaSpace.jingan.mapper.JaSjkjActivityMapper;
import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityDto;
import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityRegistrationDto;
import com.tongtech.smzy.areaSpace.jingan.service.JaSjkjActivityMobileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.List;

@Service
public class JaSjkjActivityMobileServiceImpl implements JaSjkjActivityMobileService {

    @Autowired
    private JaSjkjActivityMapper activityMapper;

    @Override
    public List<JaSjkjActivityDto> selectActivityList(JaSjkjActivityDto dto) {
        return activityMapper.selectActivityList(dto);
    }

    @Override
    public int register(JaSjkjActivityDto dto) {
        JaSjkjActivityRegistrationDto registration = new JaSjkjActivityRegistrationDto();
        registration.setActivityId(dto.getId());
        registration.setRegisterTime(new Date());
        return activityMapper.insertRegistration(registration);
    }
}
