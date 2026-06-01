import { ref } from "vue";

export function useColumns() {
  const columns = ref([
    { label: "ID", prop: "id" },
    { label: "Name", prop: "name" },
  ]);
  return { columns };
}
