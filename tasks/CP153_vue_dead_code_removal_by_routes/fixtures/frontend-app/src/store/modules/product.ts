import { defineStore } from "pinia";

export const useProductStore = defineStore("product", {
  state: () => ({
    catalog: [],
    pricingRules: [],
  }),
  actions: {
    async fetchCatalog() {
      // fetch logic
    }
  }
});
