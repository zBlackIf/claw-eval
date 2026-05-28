package com.tongtech.smzy.areaSpace.jingan.controller;

import com.tongtech.common.core.controller.BaseController;
import com.tongtech.common.core.page.TableDataInfo;
import com.tongtech.smzy.areaSpace.jingan.pojo.dto.JaSjkjActivityDto;
import com.tongtech.smzy.areaSpace.jingan.service.JaSjkjActivityAdminService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/jingan/sjkj/activity/admin")
public class JaSjkjActivityAdminController extends BaseController {

    @Autowired
    private JaSjkjActivityAdminService adminService;

    @GetMapping("/selectActivityList")
    public TableDataInfo selectActivityList(JaSjkjActivityDto dto) {
        startPage();
        return getDataTable(adminService.selectActivityList(dto));
    }

    @GetMapping("/detail/{id}")
    public Object detail(@PathVariable Long id) {
        return success(adminService.detail(id));
    }

    @PostMapping("/register")
    public Object register(@RequestBody JaSjkjActivityDto dto) {
        return toAjax(adminService.register(dto));
    }
}
