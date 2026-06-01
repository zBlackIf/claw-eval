using System;

namespace MediNet.Data.Models
{
    /// <summary>
    /// 财务系统退款请求 DTO
    /// </summary>
    public class FinancialSystemRefundDto
    {
        /// <summary>
        /// 订单编号
        /// </summary>
        public string OrderCode { get; set; }

        /// <summary>
        /// 退款金额（分），为空则全额退款
        /// </summary>
        public long? RefundAmount { get; set; }

        /// <summary>
        /// 退款原因
        /// </summary>
        public string RefundReason { get; set; }

        /// <summary>
        /// 操作人姓名
        /// </summary>
        public string OperatorName { get; set; }

        /// <summary>
        /// 订单类型（前端传入，用于路由到不同退款通道）
        /// </summary>
        public OrderTypeEnum? OrderType { get; set; }
    }

    public enum OrderTypeEnum
    {
        AppointmentOrder = 1,  // 预约单
        ShopOrder = 2          // 商城单
    }

    public enum OrderStatusEnum
    {
        Pending = 0,
        Paid = 1,
        Refunding = 2,
        Refunded = 3,
        Closed = 4
    }
}
