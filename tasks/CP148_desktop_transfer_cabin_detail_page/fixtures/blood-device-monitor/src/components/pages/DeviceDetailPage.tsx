'use client';

import { useAppStore } from '@/store/use-app-store';
import { statusColors, statusTextMap, deviceNameMap } from '@/lib/mock-data';

/**
 * DeviceDetailPage - 设备详情二级页面
 *
 * 当前支持的设备类型:
 * - 自动分拣机 (AutoSorter)
 * - 速冻机 (QuickFreezer)
 * - 离心机 (Centrifuge)
 *
 * TODO: 桌面式交接舱 (DesktopTransferCabin) 的二级页面尚未实现
 */
export function DeviceDetailPage() {
  const { selectedDevice, selectDevice } = useAppStore();

  if (!selectedDevice) return null;

  const deviceType = getDeviceType(selectedDevice.name);

  return (
    <main className="min-h-screen bg-slate-900 text-white">
      {/* 顶部导航 */}
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center px-6">
        <button
          onClick={() => selectDevice(null)}
          className="text-cyan-400 hover:text-cyan-300 mr-4"
        >
          &larr; 返回
        </button>
        <h1 className="text-lg font-semibold">{selectedDevice.name} - 详情</h1>
        <span
          className="ml-4 px-2 py-0.5 rounded text-xs"
          style={{ backgroundColor: statusColors[selectedDevice.status] }}
        >
          {statusTextMap[selectedDevice.status]}
        </span>
      </header>

      {/* 内容区 */}
      <div className="flex h-[calc(100vh-3.5rem)]">
        {/* 左侧面板 */}
        <aside className="w-80 bg-slate-800/50 border-r border-slate-700 p-4 overflow-y-auto">
          {deviceType === 'auto_sorter' && <AutoSorterLeftPanel />}
          {deviceType === 'quick_freezer' && <QuickFreezerLeftPanel />}
          {deviceType === 'centrifuge' && <CentrifugeLeftPanel />}
          {/* 桌面式交接舱暂无实现 */}
        </aside>

        {/* 右侧主内容 */}
        <section className="flex-1 p-6 overflow-y-auto">
          {deviceType === 'auto_sorter' && <AutoSorterRightPanel />}
          {deviceType === 'quick_freezer' && <QuickFreezerRightPanel />}
          {deviceType === 'centrifuge' && <CentrifugeRightPanel />}
          {/* 桌面式交接舱暂无实现 */}
        </section>
      </div>
    </main>
  );
}

function getDeviceType(name: string): string {
  const map: Record<string, string> = {
    '自动分拣机': 'auto_sorter',
    '速冻机': 'quick_freezer',
    '离心机': 'centrifuge',
    '桌面式交接舱': 'desktop_transfer_cabin',
    '病毒灭活监测仪': 'virus_inactivation',
  };
  return map[name] || 'unknown';
}

// ==================== 自动分拣机 ====================

function AutoSorterLeftPanel() {
  return (
    <div className="space-y-4">
      <GlassCard title="设备信息">
        <InfoRow label="设备编号" value="ASM-2024-001" />
        <InfoRow label="工作状态" value="运行中" />
        <InfoRow label="今日分拣" value="156 袋" />
      </GlassCard>
      <GlassCard title="当前批次">
        <InfoRow label="批次号" value="BATCH-20240615-001" />
        <InfoRow label="已分拣" value="23/30" />
      </GlassCard>
    </div>
  );
}

function AutoSorterRightPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-cyan-400">分拣详情</h2>
      <div className="bg-slate-800 rounded-lg p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-600 text-left">
              <th className="py-2 px-3">献血码</th>
              <th className="py-2 px-3">血型</th>
              <th className="py-2 px-3">规格</th>
              <th className="py-2 px-3">品类</th>
              <th className="py-2 px-3">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-700">
              <td className="py-2 px-3">D20240001</td>
              <td className="py-2 px-3">A</td>
              <td className="py-2 px-3">400ml</td>
              <td className="py-2 px-3">全血</td>
              <td className="py-2 px-3 text-green-400">已分拣</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== 速冻机 ====================

function QuickFreezerLeftPanel() {
  return (
    <div className="space-y-4">
      <GlassCard title="设备信息">
        <InfoRow label="设备编号" value="QF-2024-001" />
        <InfoRow label="工作状态" value="运行中" />
        <InfoRow label="当前温度" value="-40°C" />
      </GlassCard>
      <GlassCard title="速冻程序">
        <InfoRow label="程序名" value="快速冷冻A" />
        <InfoRow label="目标温度" value="-45°C" />
        <InfoRow label="预计时长" value="45分钟" />
      </GlassCard>
    </div>
  );
}

function QuickFreezerRightPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-cyan-400">速冻详情</h2>
      <div className="bg-slate-800 rounded-lg p-4">
        <p className="text-gray-300">速冻中的血液列表...</p>
      </div>
    </div>
  );
}

// ==================== 离心机 ====================

function CentrifugeLeftPanel() {
  return (
    <div className="space-y-4">
      <GlassCard title="设备信息">
        <InfoRow label="设备编号" value="CF-2024-001" />
        <InfoRow label="工作状态" value="空闲" />
        <InfoRow label="转速" value="3000 RPM" />
      </GlassCard>
    </div>
  );
}

function CentrifugeRightPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-cyan-400">离心详情</h2>
      <div className="bg-slate-800 rounded-lg p-4">
        <p className="text-gray-300">离心处理记录...</p>
      </div>
    </div>
  );
}

// ==================== 通用 UI 组件 ====================

function GlassCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-slate-800/60 backdrop-blur border border-slate-700 rounded-lg p-4">
      <h3 className="text-sm font-medium text-cyan-300 mb-3">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  );
}
