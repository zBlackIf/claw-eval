/**
 * 医院支付相关 API
 * 路由规则:
 *   - web/ 开头的接口不带前导 /
 *   - business/ 开头的接口带前导 /（特殊 host）
 */
import request from '@/utils/request'

// 财务汇总列表 (web/ 路径, 不带前导 /)
export function getFinancialSummaryList(params) {
  return request({
    url: 'web/financial-summary/list',
    method: 'get',
    params
  })
}

// 财务汇总详情 (web/ 路径, 不带前导 /)
export function getFinancialSummaryDetail(id) {
  return request({
    url: 'web/financial-summary/detail',
    method: 'get',
    params: { id }
  })
}

// 退款记录 (web/ 路径, 不带前导 /)
export function postAddRefund(data) {
  return request({
    url: 'web/hospital-ten-pay/refund',
    method: 'post',
    data
  })
}

// 部分退款 - 特殊 host (business/ 路径, 带前导 /)
export function postRefundPartially(data) {
  return request({
    url: '/business/HospitalTenPay/RefundPartially',
    method: 'post',
    data,
    baseURL: ApiHostEnum.SzRefund
  })
}

// TODO: 财务系统退款接口
// 原 dotnet 路由: HospitalTenPay/FinancialSystemRefundInfo
// 需要改为 Java 路由，使用 web/ 路径格式（不带前导 /）
export function postFinancialSystemRefund(data) {
  return request({
    url: 'web/hospital-ten-pay/financial-system-refund',
    method: 'post',
    data
  })
}
