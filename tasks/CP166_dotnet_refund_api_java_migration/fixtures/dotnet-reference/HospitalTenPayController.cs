using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;
using MediNet.Data.Models;
using MediNet.Data.Services;

namespace MediNet.Web.Controllers
{
    /// <summary>
    /// dotnet 路由: HospitalTenPay/FinancialSystemRefundInfo
    /// 对应 Java 路由: /api/web/hospital-ten-pay/financial-system-refund
    ///
    /// 注意: dotnet 用 PascalCase 路由 (HospitalTenPay/FinancialSystemRefundInfo)
    ///       Java 用 kebab-case 路由 (hospital-ten-pay/financial-system-refund)
    /// </summary>
    [Route("api/[controller]")]
    public class HospitalTenPayController : ControllerBase
    {
        private readonly BusinessPublicService _businessPublicService;

        public HospitalTenPayController(BusinessPublicService businessPublicService)
        {
            _businessPublicService = businessPublicService;
        }

        /// <summary>
        /// 财务系统退款接口
        /// POST HospitalTenPay/FinancialSystemRefundInfo
        /// </summary>
        [HttpPost("FinancialSystemRefundInfo")]
        public async Task<IActionResult> FinancialSystemRefundInfo([FromBody] FinancialSystemRefundDto request)
        {
            if (string.IsNullOrEmpty(request.OrderCode))
            {
                return BadRequest("订单编号不能为空");
            }

            var result = await _businessPublicService.FinancialSystemRefundInfo(request);
            return Ok(new { success = result, message = result ? "退款成功" : "退款失败" });
        }

        /// <summary>
        /// 部分退款 (已迁移到 Java)
        /// POST HospitalTenPay/RefundPartially
        /// </summary>
        [HttpPost("RefundPartially")]
        public async Task<IActionResult> RefundPartially([FromBody] RefundPartiallyRequest request)
        {
            var result = await _businessPublicService.RefundPartially(request);
            return Ok(result);
        }
    }
}
