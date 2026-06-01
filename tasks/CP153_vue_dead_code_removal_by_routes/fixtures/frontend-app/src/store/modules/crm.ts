import { defineStore } from "pinia";

export const useCrmStore = defineStore("crm", {
  state: () => ({
    customers: [],
    currentCustomer: null,
  }),
  actions: {
    async fetchCustomers() {
      // fetch logic
    }
  }
});
