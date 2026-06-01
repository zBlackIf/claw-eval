package com.myky.finance.manage.rpc;

import com.myky.finance.manage.model.dto.RefundReq;
import com.myky.common.model.Result;
import lombok.extern.slf4j.Slf4j;

/**
 * HospitalTenPayRpcClient 降级工厂
 */
@Slf4j
public class HospitalTenPayRpcClientFallbackFactory {

    public HospitalTenPayRpcClient create(Throwable cause) {
        log.error("HospitalTenPayRpcClient fallback, cause: {}", cause.getMessage());
        return new HospitalTenPayRpcClient() {
            @Override
            public Result<Void> addRefund(RefundReq req) {
                log.error("addRefund fallback for order: {}", req.getOrderCode());
                return Result.fail("服务暂时不可用");
            }

            @Override
            public Result<Object> queryRefundStatus(String orderCode) {
                log.error("queryRefundStatus fallback for order: {}", orderCode);
                return Result.fail("服务暂时不可用");
            }

            // TODO: 添加 financialSystemRefund 降级方法
        };
    }
}
