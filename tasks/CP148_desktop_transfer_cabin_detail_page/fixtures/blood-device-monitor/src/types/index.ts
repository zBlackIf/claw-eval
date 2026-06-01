// 血液信息
export interface BloodInfo {
  donationCode: string;    // 献血码
  bloodType: BloodType;    // 血型
  specification: string;   // 规格 (如 200ml, 400ml)
  category: BloodCategory; // 品类
}

export type BloodType = 'A' | 'B' | 'AB' | 'O' | 'Rh-A' | 'Rh-B' | 'Rh-AB' | 'Rh-O';

export type BloodCategory = '全血' | '红细胞' | '血小板' | '血浆' | '冷沉淀';

// 设备状态
export type DeviceStatus = 'running' | 'idle' | 'error' | 'maintenance';

// 通用设备信息
export interface DeviceInfo {
  id: string;
  name: string;
  deviceCode: string;     // 设备编号
  status: DeviceStatus;
  location: string;
}

// 工序步骤
export type ProcessStep =
  | '血液接收'
  | '成分分离'
  | '速冻处理'
  | '病毒灭活'
  | '质量检测'
  | '冷藏储存';

// 操作记录
export interface OperationRecord {
  id: string;
  operator: string;       // 操作者
  timestamp: string;      // ISO datetime
  action: string;
  deviceCode: string;
}

// 自动分拣机详细信息
export interface AutoSorterDetail {
  device: DeviceInfo;
  currentBatch: string;
  sortedCount: number;
  errorCount: number;
  bloodItems: BloodInfo[];
  records: OperationRecord[];
}

// 速冻机详细信息
export interface QuickFreezerDetail {
  device: DeviceInfo;
  temperature: number;
  programName: string;
  freezeDuration: number;   // 分钟
  bloodItems: BloodInfo[];
  records: OperationRecord[];
}

// 离心机详细信息
export interface CentrifugeDetail {
  device: DeviceInfo;
  rpm: number;
  duration: number;
  bloodItems: BloodInfo[];
  records: OperationRecord[];
}
