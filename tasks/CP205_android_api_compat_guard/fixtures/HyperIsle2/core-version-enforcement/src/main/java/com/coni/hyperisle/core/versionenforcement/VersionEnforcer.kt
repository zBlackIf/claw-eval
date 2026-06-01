package com.coni.hyperisle.core.versionenforcement

import kotlinx.coroutines.flow.StateFlow

/**
 * Validates app version against server-defined minimum and blocks outdated versions.
 *
 * Responsibilities:
 * - Fetch minimum version from RemoteConfig
 * - Compare with installed version
 * - Expose version status as observable state
 */
interface VersionEnforcer {
    /**
     * Observable state of version enforcement check.
     */
    val versionStatus: StateFlow<VersionStatus>

    /**
     * Perform an async version check against the remote server.
     * Returns the result of the check.
     */
    suspend fun checkVersion(): VersionCheckResult
}

enum class VersionStatus {
    Checking,
    Allowed,
    UpdateRequired,
    Blocked
}

sealed class VersionCheckResult {
    object Allowed : VersionCheckResult()
    data class UpdateRequired(val minVersion: String) : VersionCheckResult()
    data class Blocked(val reason: String) : VersionCheckResult()
}
