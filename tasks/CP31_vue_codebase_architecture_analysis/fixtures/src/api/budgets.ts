import request from './request'

export function getBudgetList(params: any) {
  return request({ url: '/budgets', method: 'get', params })
}

export function getBudgetById(id: number) {
  return request({ url: `/budgets/${id}`, method: 'get' })
}

export function createBudget(data: any) {
  return request({ url: '/budgets', method: 'post', data })
}

export function updateBudget(id: number, data: any) {
  return request({ url: `/budgets/${id}`, method: 'put', data })
}

export function deleteBudget(id: number) {
  return request({ url: `/budgets/${id}`, method: 'delete' })
}
