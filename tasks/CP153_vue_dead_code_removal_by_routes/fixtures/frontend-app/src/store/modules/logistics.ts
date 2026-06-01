import { defineStore } from "pinia";

export const useLogisticsStore = defineStore("logistics", {
  state: () => ({
    shipments: [],
    trackingInfo: null,
  }),
  actions: {
    async fetchShipments() {
      // fetch logic
    }
  }
});
