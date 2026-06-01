using System;
using System.Threading.Tasks;
using MediNet.Data.Enums;
using MediNet.Data.Models;
using MediNet.Data.Services.Payment;

namespace MediNet.Data.Services
{
    /// <summary>
    /// 业务公共服务 - 财务系统退款
    /// Java 迁移时需将此方法实现到 HospitalTenPayService
    /// </summary>
    public partial class BusinessPublicService
    {
        private readonly IHospitalTenPayService _hospitalTenPayService;
        private readonly IPaymentScanPayService _paymentScanPayService;

        /// <summary>
        /// 财务系统退款 - 根据订单类型走不同退款通道
        /// </summary>
        /// <param name="request">退款请求</param>
        /// <returns>退款是否成功</returns>
        public async Task<bool> FinancialSystemRefundInfo(FinancialSystemRefundDto request)
        {
            var order = await _orderRepository.GetByCodeAsync(request.OrderCode);
            if (order == null)
            {
                throw new BusinessException($"订单不存在: {request.OrderCode}");
            }

            if (order.OrderStatus == OrderStatusEnum.Refunded)
            {
                throw new BusinessException("该订单已退款，不可重复操作");
            }

            bool refundResult;

            if (order.OrderType == OrderTypeEnum.AppointmentOrder)
            {
                // 预约单 → 汇付部分退款
                refundResult = await _paymentScanPayService.RefundPartially(new RefundPartiallyRequest
                {
                    OrderCode = request.OrderCode,
                    RefundAmount = request.RefundAmount ?? order.OrderAmount,
                    RefundReason = request.RefundReason ?? "财务系统退款"
                });
            }
            else if (order.OrderType == OrderTypeEnum.ShopOrder)
            {
                // 商城单 → 微信退款
                refundResult = await _hospitalTenPayService.WeChatRefund(new WeChatRefundRequest
                {
                    OrderCode = request.OrderCode,
                    TotalFee = order.OrderAmount,
                    RefundFee = request.RefundAmount ?? order.OrderAmount,
                    RefundReason = request.RefundReason ?? "财务系统退款"
                });
            }
            else
            {
                throw new BusinessException($"不支持的订单类型: {order.OrderType}");
            }

            if (refundResult)
            {
                // 更新订单状态为已退款
                order.OrderStatus = OrderStatusEnum.Refunded;
                order.RefundTime = DateTime.Now;
                order.RefundReason = request.RefundReason;
                await _orderRepository.UpdateAsync(order);

                // 记录退款日志
                await _refundLogService.LogAsync(new RefundLog
                {
                    OrderCode = request.OrderCode,
                    RefundAmount = request.RefundAmount ?? order.OrderAmount,
                    RefundChannel = order.OrderType == OrderTypeEnum.AppointmentOrder ? "HUIFU" : "WECHAT",
                    OperatorName = request.OperatorName,
                    CreatedAt = DateTime.Now
                });
            }
            else
            {
                throw new BusinessException("退款失败，请稍后重试");
            }

            return refundResult;
        }
    }
}
