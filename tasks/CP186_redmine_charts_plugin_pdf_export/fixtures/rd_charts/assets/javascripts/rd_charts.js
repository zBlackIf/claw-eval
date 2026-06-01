/**
 * Rd Charts Plugin - Main JavaScript
 * Uses Chart.js 2.9.x (bundled with Redmine 4.2)
 */
(function() {
  'use strict';

  var RdCharts = {
    charts: {},

    init: function() {
      this.bindTabs();
      this.renderOverview();
      this.renderDimension();
      this.renderTrend();
      this.renderOverdue();
      this.renderEfficiency();
    },

    bindTabs: function() {
      var tabs = document.querySelectorAll('.rd-tab');
      tabs.forEach(function(tab) {
        tab.addEventListener('click', function(e) {
          e.preventDefault();
          var target = this.getAttribute('data-tab');
          // Deactivate all
          document.querySelectorAll('.rd-tab').forEach(function(t) { t.classList.remove('active'); });
          document.querySelectorAll('.rd-panel').forEach(function(p) { p.classList.remove('active'); });
          // Activate target
          this.classList.add('active');
          document.getElementById('panel-' + target).classList.add('active');
        });
      });
    },

    renderOverview: function() {
      var data = window.RdChartsData;
      var ctx = document.getElementById('chart-overview-pie').getContext('2d');
      this.charts['overview-pie'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Open', 'Closed', 'Overdue'],
          datasets: [{
            data: [data.open - data.overdue, data.closed, data.overdue],
            backgroundColor: ['#4caf50', '#2196f3', '#f44336']
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          legend: { position: 'bottom' }
        }
      });
    },

    renderDimension: function() {
      var data = window.RdChartsData;

      // By Tracker
      var trackerCtx = document.getElementById('chart-by-tracker').getContext('2d');
      this.charts['by-tracker'] = new Chart(trackerCtx, {
        type: 'bar',
        data: {
          labels: Object.keys(data.byTracker),
          datasets: [{
            label: 'Issues by Tracker',
            data: Object.values(data.byTracker),
            backgroundColor: '#42a5f5'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

      // By Priority
      var prioCtx = document.getElementById('chart-by-priority').getContext('2d');
      this.charts['by-priority'] = new Chart(prioCtx, {
        type: 'horizontalBar',
        data: {
          labels: Object.keys(data.byPriority),
          datasets: [{
            label: 'Issues by Priority',
            data: Object.values(data.byPriority),
            backgroundColor: '#ff7043'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

      // By Assignee
      var assCtx = document.getElementById('chart-by-assignee').getContext('2d');
      this.charts['by-assignee'] = new Chart(assCtx, {
        type: 'pie',
        data: {
          labels: Object.keys(data.byAssignee),
          datasets: [{
            data: Object.values(data.byAssignee),
            backgroundColor: ['#66bb6a', '#42a5f5', '#ab47bc', '#ffa726', '#ef5350', '#26c6da']
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, legend: { position: 'right' } }
      });
    },

    renderTrend: function() {
      var data = window.RdChartsData;
      var ctx = document.getElementById('chart-trend-line').getContext('2d');
      this.charts['trend-line'] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: Object.keys(data.weeklyCreated),
          datasets: [
            {
              label: 'Created',
              data: Object.values(data.weeklyCreated),
              borderColor: '#42a5f5',
              fill: false
            },
            {
              label: 'Closed',
              data: Object.values(data.weeklyClosed),
              borderColor: '#66bb6a',
              fill: false
            }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    },

    renderOverdue: function() {
      var ctx = document.getElementById('chart-overdue-bar').getContext('2d');
      this.charts['overdue-bar'] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['This Week', 'Last Week', '2 Weeks Ago', '3+ Weeks'],
          datasets: [{
            label: 'Overdue Issues',
            data: [3, 5, 2, 8],
            backgroundColor: '#ef5350'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    },

    renderEfficiency: function() {
      var ctx = document.getElementById('chart-efficiency-radar').getContext('2d');
      this.charts['efficiency-radar'] = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: ['Response Time', 'Resolution Rate', 'Reopened Rate', 'SLA Compliance', 'Throughput'],
          datasets: [{
            label: 'Team Efficiency',
            data: [75, 82, 15, 90, 68],
            backgroundColor: 'rgba(66,165,245,0.2)',
            borderColor: '#42a5f5'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }
  };

  document.addEventListener('DOMContentLoaded', function() {
    if (window.RdChartsData) {
      RdCharts.init();
    }
  });

  window.RdCharts = RdCharts;
})();
