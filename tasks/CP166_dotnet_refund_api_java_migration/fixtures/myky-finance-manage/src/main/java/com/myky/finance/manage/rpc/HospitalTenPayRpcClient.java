package com.myky.finance.manage.rpc;

import com.myky.finance.manage.model.dto.RefundReq;
import com.myky.common.model.Result;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.service.annotation.GetExchange;
import org.springframework.web.service.annotation.PostExchange;

/**
 * 医院支付服务 RPC 客户端
 * 调用 myky-inter-hospital 服务的 /api/gw/hospital-ten-pay/ 接口
 */
public interface HospitalTenPayRpcClient {

    @PostExchange("/api/gw/hospital-ten-pay/refund")
    Result<Void> addRefund(@RequestBody RefundReq req);

    @GetExchange("/api/gw/hospital-ten-pay/refund/query")
    Result<Object> queryRefundStatus(@RequestParam String orderCode);

    // TODO: 添加 financialSystemRefund 的 RPC 调用
    //       对应 inter-hospital 服务接口: /api/gw/hospital-ten-pay/financial-system-refund
}
