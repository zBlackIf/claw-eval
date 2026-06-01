package com.myky.finance.manage.web.controller;

import com.myky.finance.manage.core.service.HospitalTenPayService;
import com.myky.finance.manage.model.dto.RefundReq;
import com.myky.common.model.Result;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 医院支付管理控制器
 * 当前已实现: /refund (记录退款), /refund/query (查询退款状态)
 * TODO: 需要迁移 dotnet FinancialSystemRefundInfo 接口到 Java
 */
@RestController
@RequestMapping("/api/web/hospital-ten-pay")
@RequiredArgsConstructor
public class HospitalTenPayController {

    private final HospitalTenPayService hospitalTenPayService;

    /**
     * 记录退款操作
     */
    @PostMapping("/refund")
    public Result<Void> addRefund(@RequestBody RefundReq req) {
        hospitalTenPayService.addRefund(req);
        return Result.success();
    }

    /**
     * 查询退款状态
     */
    @GetMapping("/refund/query")
    public Result<Object> queryRefundStatus(@RequestParam String orderCode) {
        return Result.success(hospitalTenPayService.queryRefundStatus(orderCode));
    }

    // TODO: 迁移 dotnet HospitalTenPay/FinancialSystemRefundInfo 接口
    //       对应 Java 路由: /financial-system-refund
    //       参见 dotnet-reference/ 目录下的 .NET 源码
}
