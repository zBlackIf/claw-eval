/**
 * Utility: find nested object in form column config by prop name.
 * Used by change-runner to locate field definitions.
 *
 * @param {Array} list - Column configuration array (nested via children.column)
 * @param {string} prop - The prop name to search for
 * @returns {object|undefined} The matched column config object
 */
export function findObject(list, prop) {
  if (!list || !Array.isArray(list)) return undefined
  for (const item of list) {
    if (item.prop === prop) return item
    if (item.children && item.children.column) {
      const found = findObject(item.children.column, prop)
      if (found) return found
    }
  }
  return undefined
}
