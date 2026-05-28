package com.tongtech.smzy.areaSpace.jingan.controller;

import com.tongtech.common.core.controller.BaseController;
import com.tongtech.common.core.page.TableDataInfo;
import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityDto;
import com.tongtech.smzy.areaSpace.jingan.service.JaSjkjActivityMobileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/jingan/sjkj/activity/mobile")
public class JaSjkjActivityMobileController extends BaseController {

    @Autowired
    private JaSjkjActivityMobileService mobileService;

    @GetMapping("/selectActivityList")
    public TableDataInfo selectActivityList(JaSjkjActivityDto dto) {
        startPage();
        return getDataTable(mobileService.selectActivityList(dto));
    }

    @PostMapping("/register")
    public Object register(@RequestBody JaSjkjActivityDto dto) {
        return toAjax(mobileService.register(dto));
    }
}
