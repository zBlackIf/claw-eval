import type {
  BloodInfo,
  BloodType,
  BloodCategory,
  DeviceInfo,
  DeviceStatus,
  OperationRecord,
  AutoSorterDetail,
  QuickFreezerDetail,
  CentrifugeDetail,
} from '@/types';

// 设备名称映射
export const deviceNameMap: Record<string, string> = {
  auto_sorter: '自动分拣机',
  quick_freezer: '速冻机',
  centrifuge: '离心机',
  desktop_transfer_cabin: '桌面式交接舱',
  virus_inactivation: '病毒灭活监测仪',
};

// 设备状态颜色
export const statusColors: Record<DeviceStatus, string> = {
  running: '#10b981',
  idle: '#6b7280',
  error: '#ef4444',
  maintenance: '#f59e0b',
};

// 设备状态文本
export const statusTextMap: Record<DeviceStatus, string> = {
  running: '运行中',
  idle: '空闲',
  error: '故障',
  maintenance: '维护中',
};

// 模拟血液数据
export const mockBloodItems: BloodInfo[] = [
  { donationCode: 'D20240001', bloodType: 'A', specification: '400ml', category: '全血' },
  { donationCode: 'D20240002', bloodType: 'B', specification: '200ml', category: '红细胞' },
  { donationCode: 'D20240003', bloodType: 'O', specification: '400ml', category: '血浆' },
  { donationCode: 'D20240004', bloodType: 'AB', specification: '200ml', category: '血小板' },
  { donationCode: 'D20240005', bloodType: 'A', specification: '400ml', category: '冷沉淀' },
  { donationCode: 'D20240006', bloodType: 'O', specification: '200ml', category: '全血' },
  { donationCode: 'D20240007', bloodType: 'B', specification: '400ml', category: '红细胞' },
  { donationCode: 'D20240008', bloodType: 'Rh-A', specification: '200ml', category: '血浆' },
];

// 模拟设备列表
export const mockDevices: DeviceInfo[] = [
  { id: 'dev-001', name: '自动分拣机', deviceCode: 'ASM-2024-001', status: 'running', location: '1号分拣室' },
  { id: 'dev-002', name: '速冻机', deviceCode: 'QF-2024-001', status: 'running', location: '冷冻室A' },
  { id: 'dev-003', name: '离心机', deviceCode: 'CF-2024-001', status: 'idle', location: '分离室' },
  { id: 'dev-004', name: '桌面式交接舱', deviceCode: 'DTC-2024-001', status: 'running', location: '交接区A' },
  { id: 'dev-005', name: '桌面式交接舱', deviceCode: 'DTC-2024-002', status: 'idle', location: '交接区B' },
  { id: 'dev-006', name: '病毒灭活监测仪', deviceCode: 'VI-2024-001', status: 'running', location: '灭活室' },
];

// 模拟操作记录
export const mockRecords: OperationRecord[] = [
  { id: 'r-001', operator: '张三', timestamp: '2024-06-15T08:30:00', action: '启动接驳', deviceCode: 'DTC-2024-001' },
  { id: 'r-002', operator: '李四', timestamp: '2024-06-15T09:15:00', action: '批次完成', deviceCode: 'DTC-2024-001' },
  { id: 'r-003', operator: '张三', timestamp: '2024-06-15T10:00:00', action: '热合完成', deviceCode: 'DTC-2024-001' },
  { id: 'r-004', operator: '王五', timestamp: '2024-06-15T10:45:00', action: '启动接驳', deviceCode: 'DTC-2024-002' },
];
