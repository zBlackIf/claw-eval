/**
 * DeviceService - Manages firefighting robot devices
 * Handles device registration, status, and control commands
 */
const EventEmitter = require('events');
const logger = require('./LoggerService');

class DeviceService extends EventEmitter {
  constructor() {
    super();
    this.devices = new Map();
  }

  registerDevice(deviceId, deviceInfo) {
    this.devices.set(deviceId, {
      ...deviceInfo,
      status: 'online',
      registeredAt: new Date().toISOString()
    });
    logger.info(`Device registered: ${deviceId}`);
    this.emit('device:registered', { deviceId, deviceInfo });
  }

  controlDevice(deviceId, command, params = {}) {
    const device = this.devices.get(deviceId);
    if (!device) {
      throw new Error(`Device not found: ${deviceId}`);
    }
    logger.info(`Device control: ${deviceId} -> ${command}`, params);
    this.emit('device:control', { deviceId, command, params, timestamp: new Date().toISOString() });
    return { success: true, deviceId, command, params };
  }

  getDeviceStatus(deviceId) {
    return this.devices.get(deviceId) || null;
  }

  setDeviceOffline(deviceId) {
    const device = this.devices.get(deviceId);
    if (device) {
      device.status = 'offline';
      device.lastOffline = new Date().toISOString();
      this.emit('device:offline', { deviceId });
    }
  }
}

module.exports = new DeviceService();
