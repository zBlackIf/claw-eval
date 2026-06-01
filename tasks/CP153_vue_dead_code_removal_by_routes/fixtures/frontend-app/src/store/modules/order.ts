import { defineStore } from "pinia";

export const useOrderStore = defineStore("order", {
  state: () => ({
    orderList: [],
    currentOrder: null,
    loading: false,
  }),
  actions: {
    async fetchOrders() {
      this.loading = true;
      // fetch logic
      this.loading = false;
    }
  }
});
