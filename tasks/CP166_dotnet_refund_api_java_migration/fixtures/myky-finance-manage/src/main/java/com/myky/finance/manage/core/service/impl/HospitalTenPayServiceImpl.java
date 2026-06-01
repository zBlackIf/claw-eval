package com.myky.finance.manage.core.service.impl;

import com.myky.finance.manage.core.service.HospitalTenPayService;
import com.myky.finance.manage.model.dto.RefundReq;
import com.myky.finance.manage.rpc.HospitalTenPayRpcClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@RequiredArgsConstructor
public class HospitalTenPayServiceImpl implements HospitalTenPayService {

    private final HospitalTenPayRpcClient rpcClient;

    @Override
    public void addRefund(RefundReq req) {
        log.info("Processing refund for order: {}", req.getOrderCode());
        rpcClient.addRefund(req);
    }

    @Override
    public Object queryRefundStatus(String orderCode) {
        return rpcClient.queryRefundStatus(orderCode);
    }

    // TODO: 实现 financialSystemRefund 方法
    //       dotnet 逻辑:
    //       1. 判断 orderType
    //       2. 预约单(AppointmentOrder) → 调 PaymentScanPayRefundPartially (汇付部分退款)
    //       3. 商城单(ShopOrder) → 调 WeChatRefund (微信退款)
    //       4. 退款成功后更新订单状态为 Refunded
    //       5. 退款失败抛异常并记录日志
}
