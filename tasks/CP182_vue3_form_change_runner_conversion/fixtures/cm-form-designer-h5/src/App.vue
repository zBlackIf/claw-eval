<template>
  <div id="app">
    <van-form @submit="onSubmit">
      <template v-for="col in formColumns" :key="col.prop">
        <cm-form-item
          :column="col"
          :form="form"
          @change="handleFieldChange"
        />
      </template>
      <van-button type="primary" native-type="submit">Submit</van-button>
    </van-form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import CmFormItem from '../plugin/fields/cm-form-item/index.vue'

// Form data (reactive)
const form = ref({})

// Form column config - loaded from backend
const formColumns = ref([])

// Global options passed to change handlers
const globalOptions = {
  axios: null // will be set after app init
}

/**
 * TODO: Implement the change-runner module at:
 *   plugin/utils/change-runner.js
 *
 * Requirements:
 * 1. Convert from Vue 2 mixin to standalone ES module (composable or pure functions)
 * 2. Fix the WeakMap bug (cannot use string keys)
 * 3. Replace eval() with new Function() approach
 * 4. Add cache size limit to prevent memory leaks
 * 5. Replace `this` references with explicit context parameter
 * 6. Add proper error handling with console.warn
 * 7. Remove uni-app conditional compilation directives (#ifdef)
 * 8. Export: createChangeContext, resolveChangeHandler, runFieldChange
 */

function handleFieldChange(prop, value) {
  // This should call the converted change-runner
  console.log('Field changed:', prop, value)
}

function onSubmit() {
  console.log('Form submitted:', form.value)
}

onMounted(() => {
  // Simulate loading form config
  formColumns.value = [
    {
      prop: 'input1',
      label: 'Input 1',
      type: 'input',
      change: '({ value }) => { const input2 = this.findObject(this.option.column, "input2"); if (input2) input2.display = value !== "" }'
    },
    {
      prop: 'input2',
      label: 'Input 2',
      type: 'input',
      display: false,
      change: ({ value }) => {
        const input1 = this.findObject(this.option.column, 'input1')
        if (value === 'reset') input1.value = ''
      }
    },
    {
      prop: 'select1',
      label: 'Select',
      type: 'select',
      change: 'change:({ value }) => { console.log("selected:", value) },'
    }
  ]
})
</script>
