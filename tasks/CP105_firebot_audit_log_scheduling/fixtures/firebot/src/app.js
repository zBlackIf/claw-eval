const path = require('path');
const fs = require('fs');

const DeviceService = require('./services/DeviceService');
const AlarmService = require('./services/AlarmService');
const TaskDispatcher = require('./services/TaskDispatcher');
const LoggerService = require('./services/LoggerService');

class FireBot {
  constructor(baseDir = process.cwd()) {
    this.baseDir = baseDir;
    this.filesDir = path.join(baseDir, 'files');
    fs.mkdirSync(this.filesDir, { recursive: true });

    this.logger = new LoggerService(baseDir);
    this.deviceService = new DeviceService();
    this.alarmService = new AlarmService();
    this.taskDispatcher = new TaskDispatcher();

    this._setupEventListeners();
  }

  _setupEventListeners() {
    this.alarmService.on('alarm:triggered', (alarm) => {
      this.logger.warn('AlarmService', `Alarm triggered: ${alarm.alarmId}`, { alarm });
    });

    this.deviceService.on('device:controlled', (result) => {
      this.logger.info('DeviceService', `Device controlled: ${result.deviceId}`, { result });
    });
  }

  async start() {
    this.logger.info('FireBot', 'System started');
    return this;
  }

  async stop() {
    this.logger.info('FireBot', 'System stopped');
  }
}

module.exports = FireBot;
