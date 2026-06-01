class TaskDispatcher {
  constructor() {
    this.taskQueue = [];
    this.history = [];
  }

  async dispatch(taskType, target, payload = {}) {
    const task = {
      taskId: `TSK-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      taskType,
      target,
      payload,
      dispatchedAt: new Date().toISOString(),
      status: 'dispatched'
    };
    this.taskQueue.push(task);
    this.history.push(task);
    return task;
  }

  async completeTask(taskId, result = {}) {
    const idx = this.taskQueue.findIndex(t => t.taskId === taskId);
    if (idx === -1) throw new Error(`Task ${taskId} not in queue`);
    const task = this.taskQueue.splice(idx, 1)[0];
    task.status = 'completed';
    task.completedAt = new Date().toISOString();
    task.result = result;
    return task;
  }

  getPendingTasks() {
    return this.taskQueue.filter(t => t.status === 'dispatched');
  }

  getHistory() {
    return this.history;
  }
}

module.exports = TaskDispatcher;
