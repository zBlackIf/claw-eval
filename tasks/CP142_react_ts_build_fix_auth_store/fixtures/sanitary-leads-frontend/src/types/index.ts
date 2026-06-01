export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  avatar?: string;
  createdAt: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface Merchant {
  id: string;
  name: string;
  platform: 'douyin' | 'kuaishou' | '1688' | 'taobao' | 'pinduoduo';
  contact: string;
  phone?: string;
  wechat?: string;
  region: string;
  category: string;
  score: number;
  createdAt: string;
}

export interface CrawlTask {
  id: string;
  platform: string;
  keyword: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  totalResults: number;
  createdAt: string;
  finishedAt?: string;
}
