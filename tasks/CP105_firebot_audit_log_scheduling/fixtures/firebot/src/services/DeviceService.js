const EventEmitter = require('events');

class DeviceService extends EventEmitter {
  constructor() {
    super();
    this.devices = new Map();
  }

  async registerDevice(deviceId, config) {
    this.devices.set(deviceId, { ...config, status: 'online', lastSeen: Date.now() });
    this.emit('device:registered', { deviceId, config });
    return { success: true, deviceId };
  }

  async controlDevice(deviceId, command, params = {}) {
    const device = this.devices.get(deviceId);
    if (!device) throw new Error(`Device ${deviceId} not found`);

    const result = {
      deviceId,
      command,
      params,
      timestamp: new Date().toISOString(),
      status: 'executed'
    };
    this.emit('device:controlled', result);
    return result;
  }

  async getDeviceStatus(deviceId) {
    return this.devices.get(deviceId) || null;
  }
}

module.exports = DeviceService;
