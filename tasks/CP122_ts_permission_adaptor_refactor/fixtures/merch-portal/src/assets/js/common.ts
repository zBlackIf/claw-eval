/*
 * @Author: admin
 * @Date: 2022-03-10 09:15:00
 * @Description: 公共方法
 */

/**
 * 解析 URL query 参数
 */
export const queryStringParse = (url?: string): Record<string, string> => {
  const search = url || window.location.search
  const params: Record<string, string> = {}
  new URLSearchParams(search).forEach((v, k) => {
    params[k] = v
  })
  return params
}

/**
 * 按钮权限检查
 * @param permKey 权限标识
 * @returns boolean
 */
export const btnPermission = (permKey: string): boolean => {
  const perms: string[] = (window as any).__USER_PERMISSIONS__ || []
  return perms.includes(permKey)
}

/**
 * 防抖等待
 */
export const timeWaitingFn = (fn: Function, delay = 300) => {
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: any[]) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}
