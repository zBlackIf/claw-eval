package com.coni.hyperisle.core.versionenforcement

/**
 * Contract for version enforcement checking.
 */
interface VersionEnforcer {
    val versionStatus: VersionStatus
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
    object Blocked : VersionCheckResult()
    object Error : VersionCheckResult()
}
