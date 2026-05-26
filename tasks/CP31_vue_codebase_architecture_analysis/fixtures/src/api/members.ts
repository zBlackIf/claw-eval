import request from './request'

export function getMemberList(params: any) {
  return request({ url: '/members', method: 'get', params })
}

export function getMemberById(id: number) {
  return request({ url: `/members/${id}`, method: 'get' })
}

export function createMember(data: any) {
  return request({ url: '/members', method: 'post', data })
}

export function updateMember(id: number, data: any) {
  return request({ url: `/members/${id}`, method: 'put', data })
}

export function deleteMember(id: number) {
  return request({ url: `/members/${id}`, method: 'delete' })
}

export function getMemberPermissions(id: number) {
  return request({ url: `/members/${id}/permissions`, method: 'get' })
}
