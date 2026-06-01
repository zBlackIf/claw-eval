/**
 * App configuration
 */
module.exports = {
  app: {
    name: 'FireBot',
    version: '2.1.0'
  },
  paths: {
    files: process.env.FIREBOT_FILES || './files',
    logs: 'logs',
    // audit directory TBD
  },
  devices: {
    heartbeatInterval: 5000,
    offlineThreshold: 15000
  },
  tasks: {
    maxConcurrent: 3,
    defaultTimeout: 300000
  }
};
