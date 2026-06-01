import { defineStore } from "pinia";

export const useInventoryStore = defineStore("inventory", {
  state: () => ({
    stockList: [],
    transfers: [],
  }),
  actions: {
    async fetchStock() {
      // fetch logic
    },
    async createTransfer(data: any) {
      // transfer logic
    }
  }
});
