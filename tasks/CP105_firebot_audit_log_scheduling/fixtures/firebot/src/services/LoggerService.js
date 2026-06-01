const path = require('path');
const fs = require('fs');

class LoggerService {
  constructor(baseDir) {
    this.logDir = path.join(baseDir, 'files', 'logs');
    fs.mkdirSync(this.logDir, { recursive: true });
  }

  log(level, component, message, meta = {}) {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      ...meta
    };
    const logFile = path.join(this.logDir, `${this._today()}.log`);
    fs.appendFileSync(logFile, JSON.stringify(entry) + '\n');
    return entry;
  }

  _today() {
    return new Date().toISOString().slice(0, 10);
  }

  info(component, message, meta) { return this.log('info', component, message, meta); }
  warn(component, message, meta) { return this.log('warn', component, message, meta); }
  error(component, message, meta) { return this.log('error', component, message, meta); }
}

module.exports = LoggerService;
