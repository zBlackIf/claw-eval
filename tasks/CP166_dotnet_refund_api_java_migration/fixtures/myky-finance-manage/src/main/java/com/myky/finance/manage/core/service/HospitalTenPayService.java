package com.myky.finance.manage.core.service;

import com.myky.finance.manage.model.dto.RefundReq;

/**
 * 医院支付服务接口
 */
public interface HospitalTenPayService {

    /**
     * 记录退款
     */
    void addRefund(RefundReq req);

    /**
     * 查询退款状态
     */
    Object queryRefundStatus(String orderCode);

    // TODO: 添加 financialSystemRefund 方法
    //       需要按订单类型分支: 预约单走汇付部分退款, 商城单走微信退款
}
