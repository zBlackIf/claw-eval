/**
 * Common utility functions for the EMP application.
 */

/**
 * Check if the current user has the specified button/action permission.
 * @param permKey - Permission key string
 * @returns true if user has the permission, false otherwise
 */
export function btnPermission(permKey: string): boolean {
  // In production, this checks against the user's permission list
  // For this codebase, we provide a stub implementation
  const userPermissions = (window as any).__USER_PERMISSIONS__ || []
  return userPermissions.includes(permKey)
}

/**
 * Parse query string into object.
 */
export function queryStringParse(qs: string): Record<string, string> {
  const params: Record<string, string> = {}
  const searchParams = new URLSearchParams(qs)
  searchParams.forEach((value, key) => {
    params[key] = value
  })
  return params
}

/**
 * Get MCC description text.
 */
export function getMccDesc(code: string): string {
  return `MCC-${code}`
}

/**
 * Get region description text.
 */
export function getRegionDesc(code: string): string {
  return `Region-${code}`
}
