package com.tongtech.smzy.areaSpace.jingan.mapper;

import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityDto;
import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityRegistrationDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface JaSjkjActivityMapper {

    List<JaSjkjActivityDto> selectActivityList(JaSjkjActivityDto dto);

    JaSjkjActivityDto selectActivityById(@Param("id") Long id);

    int insertRegistration(JaSjkjActivityRegistrationDto dto);

    JaSjkjActivityRegistrationDto selectRegistrationByUserAndActivity(
            @Param("userId") String userId, @Param("activityId") Long activityId);

    int countRegistrationsByActivity(@Param("activityId") Long activityId);
}
