package com.myky.finance.manage.model.dto;

import lombok.Data;

/**
 * 退款请求 DTO
 */
@Data
public class RefundReq {
    /**
     * 订单编号
     */
    private String orderCode;

    /**
     * 退款原因
     */
    private String refundReason;

    /**
     * 退款金额（分）
     */
    private Long refundAmount;
}
