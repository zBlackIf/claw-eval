/**
 * Goods API module.
 * Backend search endpoint: POST /api/goods/search
 * Request body: { keyword: string, platform: number, page: number, size: number }
 *   platform: 0=all, 1=taobao, 2=jd, 3=pdd
 * Response: { code: 1, data: { list: GoodsItem[], total: number } }
 */

import { request } from '../utils/request'

export interface GoodsItem {
  id: string
  title: string
  price: number
  originalPrice: number
  imageUrl: string
  shopName: string
  sales: number
  platform: number  // 1=taobao, 2=jd, 3=pdd
  couponAmount?: number
  commissionRate?: number
}

export interface SearchParams {
  keyword: string
  platform?: number
  page?: number
  size?: number
}

export interface SearchResponse {
  code: number
  data: {
    list: GoodsItem[]
    total: number
  }
}

/**
 * Search goods from backend.
 * When platform=0, backend returns mixed results from all platforms.
 * For per-platform queries, use platform=1/2/3.
 */
export function searchGoods(params: SearchParams): Promise<SearchResponse> {
  return request.post('/api/goods/search', {
    keyword: params.keyword || '',
    platform: params.platform ?? 0,
    page: params.page ?? 1,
    size: params.size ?? 20,
  })
}
