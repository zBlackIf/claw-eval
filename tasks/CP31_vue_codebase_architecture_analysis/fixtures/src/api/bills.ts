import request from './request'

export function getBillList(params: any) {
  return request({ url: '/bills', method: 'get', params })
}

export function getBillById(id: number) {
  return request({ url: `/bills/${id}`, method: 'get' })
}

export function createBill(data: any) {
  return request({ url: '/bills', method: 'post', data })
}

export function updateBill(id: number, data: any) {
  return request({ url: `/bills/${id}`, method: 'put', data })
}

export function deleteBill(id: number) {
  return request({ url: `/bills/${id}`, method: 'delete' })
}

export function exportBills(params: any) {
  return request({ url: '/bills/export', method: 'get', params, responseType: 'blob' })
}
