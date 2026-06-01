/**
 * LoggerService - Application runtime logger (for developers)
 * Uses winston for structured logging to FireBot files/logs/
 */
const winston = require('winston');
const path = require('path');
const fs = require('fs-extra');

class LoggerService {
  constructor() {
    this.logDir = path.join(process.env.FIREBOT_FILES || './files', 'logs');
    fs.ensureDirSync(this.logDir);
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.File({
          filename: path.join(this.logDir, 'error.log'),
          level: 'error'
        }),
        new winston.transports.File({
          filename: path.join(this.logDir, 'combined.log')
        })
      ]
    });
  }

  info(message, meta = {}) {
    this.logger.info(message, meta);
  }

  error(message, meta = {}) {
    this.logger.error(message, meta);
  }

  warn(message, meta = {}) {
    this.logger.warn(message, meta);
  }

  debug(message, meta = {}) {
    this.logger.debug(message, meta);
  }
}

module.exports = new LoggerService();
