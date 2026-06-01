import { defineStore } from "pinia";

export const useReportStore = defineStore("report", {
  state: () => ({
    salesReport: null,
    inventoryReport: null,
  }),
  actions: {
    async fetchSalesReport(params: any) {
      // fetch logic
    }
  }
});
