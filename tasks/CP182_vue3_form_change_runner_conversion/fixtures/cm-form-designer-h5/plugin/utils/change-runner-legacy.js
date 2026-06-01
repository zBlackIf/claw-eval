/**
 * Legacy change-runner (Vue 2 / uni-app mixin style)
 * Executes dynamic form field change handlers defined in form config.
 *
 * Problems to fix during conversion:
 * 1. Uses eval() for executing change handlers - insecure
 * 2. Uses single WeakMap for both string and function keys (WeakMap cannot hold primitives)
 * 3. No cache size limit - potential memory leak
 * 4. Relies on `this` context from Vue 2 mixin (e.g., this.form, this.option)
 * 5. No error boundaries around handler execution
 */

// BUG: WeakMap cannot use string keys! This will throw TypeError at runtime.
const factoryCache = new WeakMap()

/**
 * @deprecated Uses eval() - must be replaced with new Function approach
 */
function normalizeFunctionSource(source) {
  const trimmed = String(source || '').trim()
  if (!trimmed) return ''
  // #ifdef H5 || APP
  if (trimmed.startsWith('change:')) {
    return trimmed.slice('change:'.length).trim().replace(/,$/, '')
  }
  // #endif
  return trimmed.replace(/,$/, '')
}

export default {
  methods: {
    /**
     * Find a nested object by prop name in column config
     */
    findObject(list, prop) {
      if (!list || !Array.isArray(list)) return undefined
      for (const item of list) {
        if (item.prop === prop) return item
        if (item.children && item.children.column) {
          const found = this.findObject(item.children.column, prop)
          if (found) return found
        }
      }
      return undefined
    },

    /**
     * Execute a change handler from form config.
     * change can be: string (function source) or function reference.
     *
     * In the legacy system, handlers use `this` to access:
     * - this.form (reactive form data)
     * - this.option (form schema/options)
     * - this.findObject (utility to locate fields)
     * - this.axios (HTTP client)
     */
    resolveChangeHandler(change) {
      if (!change) return undefined

      if (typeof change === 'string') {
        const source = normalizeFunctionSource(change)
        if (!source) return undefined

        // BUG: WeakMap.set() throws TypeError for string keys
        let factory = factoryCache.get(change)
        if (!factory) {
          // INSECURE: uses eval with this replacement
          const rewritten = source.replace(/this/g, '_this')
          // eslint-disable-next-line no-eval
          factory = eval(`(function(_this) { return (${rewritten}) })`)
          factoryCache.set(change, factory)
        }
        return factory(this)
      }

      if (typeof change === 'function') {
        let factory = factoryCache.get(change)
        if (factory) return factory(this)

        const source = change.toString()
        if (source.includes('this')) {
          const rewritten = source.replace(/this/g, '_this')
          // eslint-disable-next-line no-eval
          factory = eval(`(function(_this) { return (${rewritten}) })`)
          factoryCache.set(change, factory)
          return factory(this)
        }
        return change
      }

      return undefined
    },

    /**
     * Run all change handlers for a given field after value update.
     * Called by form field components on @change event.
     */
    runFieldChange(prop, value) {
      const field = this.findObject(this.option.column, prop)
      if (!field || !field.change) return

      const handler = this.resolveChangeHandler(field.change)
      if (typeof handler === 'function') {
        handler({ value, column: field, form: this.form })
      }
    }
  }
}
