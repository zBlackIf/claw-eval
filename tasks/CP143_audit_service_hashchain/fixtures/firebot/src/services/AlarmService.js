/**
 * AlarmService - Handles fire alarm events from sensors
 */
const EventEmitter = require('events');
const logger = require('./LoggerService');

class AlarmService extends EventEmitter {
  constructor() {
    super();
    this.activeAlarms = [];
  }

  triggerAlarm(alarmData) {
    const alarm = {
      id: `ALM-${Date.now()}`,
      ...alarmData,
      triggeredAt: new Date().toISOString(),
      status: 'active'
    };
    this.activeAlarms.push(alarm);
    logger.info(`Alarm triggered: ${alarm.id}`, alarmData);
    this.emit('alarm:triggered', alarm);
    return alarm;
  }

  acknowledgeAlarm(alarmId) {
    const alarm = this.activeAlarms.find(a => a.id === alarmId);
    if (alarm) {
      alarm.status = 'acknowledged';
      alarm.acknowledgedAt = new Date().toISOString();
      this.emit('alarm:acknowledged', alarm);
    }
    return alarm;
  }

  resolveAlarm(alarmId) {
    const alarm = this.activeAlarms.find(a => a.id === alarmId);
    if (alarm) {
      alarm.status = 'resolved';
      alarm.resolvedAt = new Date().toISOString();
      this.emit('alarm:resolved', alarm);
    }
    return alarm;
  }

  getActiveAlarms() {
    return this.activeAlarms.filter(a => a.status === 'active');
  }
}

module.exports = new AlarmService();
