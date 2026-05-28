export interface VideoItem {
  id: string
  title: string
  coverUrl: string
  videoUrl: string
  duration: number
  createdAt: string
  category: string
}

export interface VideoListResponse {
  list: VideoItem[]
  total: number
}

export function getVideoList(params?: { category?: string }): Promise<VideoListResponse> {
  return fetch('/api/videos', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  }).then(res => res.json())
}

export function getVideoDetail(id: string): Promise<VideoItem> {
  return fetch(`/api/videos/${id}`).then(res => res.json())
}
