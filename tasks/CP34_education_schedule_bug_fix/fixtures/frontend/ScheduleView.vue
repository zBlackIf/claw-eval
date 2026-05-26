<template>
  <div class="schedule-container">
    <h2>Course Schedule</h2>

    <div class="schedule-form">
      <div class="form-group">
        <label>Course</label>
        <select v-model="form.course_id">
          <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>

      <div class="form-group">
        <label>Teacher</label>
        <!-- BUG: :value="t" binds whole object instead of t.id -->
        <select v-model="form.teacher_id">
          <option v-for="t in teachers" :key="t.id" :value="t">{{ t.name }}</option>
        </select>
      </div>

      <div class="form-group">
        <label>Classroom</label>
        <!-- Same bug -->
        <select v-model="form.classroom_id">
          <option v-for="r in classrooms" :key="r.id" :value="r">{{ r.name }}</option>
        </select>
      </div>

      <div class="form-group">
        <label>Day of Week</label>
        <select v-model="form.day_of_week">
          <option value="Monday">Monday</option>
          <option value="Tuesday">Tuesday</option>
          <option value="Wednesday">Wednesday</option>
          <option value="Thursday">Thursday</option>
          <option value="Friday">Friday</option>
        </select>
      </div>

      <div class="form-group">
        <label>Time</label>
        <input v-model="form.start_time" type="time" />
        <span>to</span>
        <input v-model="form.end_time" type="time" />
      </div>

      <div class="form-group">
        <label>Repeat Weeks</label>
        <input v-model.number="form.repeat_weeks" type="number" min="1" max="20" />
      </div>

      <button @click="createSchedule">Add Schedule</button>
    </div>

    <table class="schedule-grid">
      <thead>
        <tr>
          <th>Time</th>
          <th v-for="day in weekdays" :key="day">{{ day }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="slot in timeSlots" :key="slot">
          <td>{{ slot }}</td>
          <td v-for="day in weekdays" :key="day">
            <div v-for="s in getSchedulesForSlot(day, slot)" :key="s.id" class="schedule-card">
              <!-- BUG: names are undefined, only IDs come from API -->
              <div class="card-course">{{ s.course_name }}</div>
              <div class="card-teacher">{{ s.teacher_name }}</div>
              <div class="card-room">{{ s.classroom_name }}</div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'ScheduleView',
  data() {
    return {
      form: {
        course_id: null, teacher_id: null, classroom_id: null,
        day_of_week: 'Monday', start_time: '09:00', end_time: '10:30', repeat_weeks: 1,
      },
      courses: [], teachers: [], classrooms: [], schedules: [],
      weekdays: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
      timeSlots: ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
    }
  },
  mounted() { this.loadData() },
  methods: {
    async loadData() {
      this.courses = await this.fetchApi('/api/courses')
      this.teachers = await this.fetchApi('/api/teachers')
      this.classrooms = await this.fetchApi('/api/classrooms')
      this.schedules = await this.fetchApi('/api/schedules')
    },
    async createSchedule() {
      const payload = { ...this.form }
      const result = await this.fetchApi('/api/schedules', 'POST', payload)
      if (result.status === 'success') {
        this.schedules.push(...result.created)
      }
    },
    getSchedulesForSlot(day, timeSlot) {
      return this.schedules.filter(s => s.day_of_week === day && s.start_time === timeSlot)
    },
    async fetchApi(url, method = 'GET', body = null) {
      const options = { method, headers: { 'Content-Type': 'application/json' } }
      if (body) options.body = JSON.stringify(body)
      const res = await fetch(url, options)
      return res.json()
    },
  },
}
</script>

<style scoped>
.schedule-card {
  background: #e3f2fd;
  border-radius: 4px;
  padding: 4px 8px;
  margin: 2px;
  font-size: 12px;
  /* BUG: No min-width set */
}
.card-course { font-weight: bold; }
.card-teacher { color: #666; }
.card-room { color: #999; font-size: 11px; }
</style>
