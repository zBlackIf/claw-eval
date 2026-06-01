import { create } from 'zustand';
import type { DeviceInfo, ProcessStep } from '@/types';
import { mockDevices } from '@/lib/mock-data';

export type ViewMode = 'dashboard' | 'device-detail';

interface AppState {
  // 当前视图
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // 当前选中的工序
  currentStep: ProcessStep;
  setCurrentStep: (step: ProcessStep) => void;

  // 当前选中的设备
  selectedDevice: DeviceInfo | null;
  selectDevice: (device: DeviceInfo | null) => void;

  // 设备列表
  devices: DeviceInfo[];
}

export const useAppStore = create<AppState>((set) => ({
  viewMode: 'dashboard',
  setViewMode: (mode) => set({ viewMode: mode }),

  currentStep: '血液接收',
  setCurrentStep: (step) => set({ currentStep: step }),

  selectedDevice: null,
  selectDevice: (device) => set({ selectedDevice: device, viewMode: device ? 'device-detail' : 'dashboard' }),

  devices: mockDevices,
}));
