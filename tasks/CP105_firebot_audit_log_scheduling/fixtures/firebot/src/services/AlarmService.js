const EventEmitter = require('events');

class AlarmService extends EventEmitter {
  constructor() {
    super();
    this.activeAlarms = new Map();
  }

  async triggerAlarm(zoneId, sensorType, severity, details = {}) {
    const alarm = {
      alarmId: `ALM-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      zoneId,
      sensorType,
      severity,
      details,
      triggeredAt: new Date().toISOString(),
      status: 'active'
    };
    this.activeAlarms.set(alarm.alarmId, alarm);
    this.emit('alarm:triggered', alarm);
    return alarm;
  }

  async acknowledgeAlarm(alarmId, operator) {
    const alarm = this.activeAlarms.get(alarmId);
    if (!alarm) throw new Error(`Alarm ${alarmId} not found`);
    alarm.status = 'acknowledged';
    alarm.acknowledgedBy = operator;
    alarm.acknowledgedAt = new Date().toISOString();
    this.emit('alarm:acknowledged', alarm);
    return alarm;
  }

  async resolveAlarm(alarmId, resolution) {
    const alarm = this.activeAlarms.get(alarmId);
    if (!alarm) throw new Error(`Alarm ${alarmId} not found`);
    alarm.status = 'resolved';
    alarm.resolution = resolution;
    alarm.resolvedAt = new Date().toISOString();
    this.activeAlarms.delete(alarmId);
    this.emit('alarm:resolved', alarm);
    return alarm;
  }

  getActiveAlarms() {
    return Array.from(this.activeAlarms.values());
  }
}

module.exports = AlarmService;
