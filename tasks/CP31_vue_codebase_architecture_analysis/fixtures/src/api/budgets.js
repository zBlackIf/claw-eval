import request from './request'
export function getBudgetList(params) {
  return request({ url: '/budgets', method: 'get', params })
}
export function createBudget(data) {
  return request({ url: '/budgets', method: 'post', data })
}
export function updateBudget(id, data) {
  return request({ url: '/budgets/' + id, method: 'put', data })
}
export function deleteBudget(id) {
  return request({ url: '/budgets/' + id, method: 'delete' })
}
