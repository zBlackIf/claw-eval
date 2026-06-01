/**
 * TaskScheduleService - Manages scheduled patrol and inspection tasks
 */
const EventEmitter = require('events');
const logger = require('./LoggerService');

class TaskScheduleService extends EventEmitter {
  constructor() {
    super();
    this.tasks = [];
    this.runningTasks = new Map();
  }

  createTask(taskConfig) {
    const task = {
      id: `TSK-${Date.now()}`,
      ...taskConfig,
      createdAt: new Date().toISOString(),
      status: 'pending'
    };
    this.tasks.push(task);
    logger.info(`Task created: ${task.id}`, taskConfig);
    this.emit('task:created', task);
    return task;
  }

  dispatchTask(taskId, targetDeviceId) {
    const task = this.tasks.find(t => t.id === taskId);
    if (!task) throw new Error(`Task not found: ${taskId}`);
    task.status = 'dispatched';
    task.targetDeviceId = targetDeviceId;
    task.dispatchedAt = new Date().toISOString();
    logger.info(`Task dispatched: ${taskId} -> ${targetDeviceId}`);
    this.emit('task:dispatched', { task, targetDeviceId });
    return task;
  }

  completeTask(taskId, result) {
    const task = this.tasks.find(t => t.id === taskId);
    if (task) {
      task.status = 'completed';
      task.completedAt = new Date().toISOString();
      task.result = result;
      this.emit('task:completed', task);
    }
    return task;
  }
}

module.exports = new TaskScheduleService();
