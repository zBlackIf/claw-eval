import { defineStore } from "pinia";

export const useSettingsStore = defineStore("settings", {
  state: () => ({
    users: [],
    roles: [],
  }),
  actions: {
    async fetchUsers() {
      // fetch logic
    }
  }
});
