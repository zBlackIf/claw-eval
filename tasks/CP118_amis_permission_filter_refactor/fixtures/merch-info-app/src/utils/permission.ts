/**
 * Permission utility for button-level access control.
 * Used in AMIS visibleOn expressions and adaptor logic.
 */

const permissionMap: Record<string, boolean> = {}

/**
 * Check if a button/feature is permitted for the current user.
 * @param key - Permission key string
 * @returns boolean indicating if the action is permitted
 */
export function btnPermission(key: string): boolean {
  return permissionMap[key] !== false
}

/**
 * Load permissions from server response.
 * Called on page init.
 */
export function loadPermissions(permissions: Record<string, boolean>): void {
  Object.assign(permissionMap, permissions)
}
