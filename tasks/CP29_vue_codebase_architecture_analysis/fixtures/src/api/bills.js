import request from './request'
export function getBillList(params) {
  return request({ url: '/bills', method: 'get', params })
}
export function createBill(data) {
  return request({ url: '/bills', method: 'post', data })
}
export function updateBill(id, data) {
  return request({ url: '/bills/' + id, method: 'put', data })
}
export function deleteBill(id) {
  return request({ url: '/bills/' + id, method: 'delete' })
}
export function getBillStats(params) {
  return request({ url: '/bills/stats', method: 'get', params })
}
export function exportBills(params) {
  return request({ url: '/bills/export', method: 'get', params, responseType: 'blob' })
}
