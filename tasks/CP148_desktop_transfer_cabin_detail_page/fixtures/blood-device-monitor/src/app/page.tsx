'use client';

import { useAppStore } from '@/store/use-app-store';
import { DeviceDetailPage } from '@/components/pages/DeviceDetailPage';

export default function Home() {
  const { viewMode, selectedDevice } = useAppStore();

  if (viewMode === 'device-detail' && selectedDevice) {
    return <DeviceDetailPage />;
  }

  return (
    <main className="min-h-screen bg-slate-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-6">血液设备监控系统</h1>
      <div className="grid grid-cols-3 gap-4">
        {/* Dashboard content - device cards would go here */}
        <p className="text-gray-400">选择设备查看详情</p>
      </div>
    </main>
  );
}
