package com.coni.hyperisle.core.versionenforcement

import com.coni.hyperisle.core.logging.UiLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Sealed class representing the version enforcement status.
 */
sealed class VersionStatus {
    object Checking : VersionStatus()
    object Allowed : VersionStatus()
    data class Blocked(val minimumVersion: String) : VersionStatus()
}

sealed class VersionCheckResult {
    object Allowed : VersionCheckResult()
    data class Blocked(val minimumVersion: String) : VersionCheckResult()
    data class Error(val message: String) : VersionCheckResult()
}

/**
 * Interface for version enforcement.
 */
interface VersionEnforcer {
    val versionStatus: StateFlow<VersionStatus>
    suspend fun checkVersion(currentVersion: String): VersionCheckResult
}

/**
 * Implementation of [VersionEnforcer] that validates app version against server-defined minimum.
 * Uses Firebase Remote Config to fetch the minimum version.
 */
class VersionEnforcerImpl(
    private val remoteConfigClient: RemoteConfigClient,
    private val cache: VersionCache
) : VersionEnforcer {

    private val _versionStatus = MutableStateFlow<VersionStatus>(VersionStatus.Checking)
    override val versionStatus: StateFlow<VersionStatus> = _versionStatus.asStateFlow()

    // BUG: No timeout on fetchMinimumVersion(). If Firebase is unresponsive,
    // the app stays in VersionStatus.Checking indefinitely, appearing frozen to users.
    override suspend fun checkVersion(currentVersion: String): VersionCheckResult {
        UiLog.sys("VersionEnforcer", "CHECK_START", mapOf("currentVersion" to currentVersion))

        val minimumVersion = fetchMinimumVersion()

        if (minimumVersion == null) {
            UiLog.err("VersionEnforcer", "NO_MINIMUM_VERSION", null)
            _versionStatus.value = VersionStatus.Allowed
            return VersionCheckResult.Allowed
        }

        return if (VersionComparator.isLessThan(currentVersion, minimumVersion)) {
            UiLog.sys("VersionEnforcer", "VERSION_BLOCKED", mapOf(
                "current" to currentVersion,
                "minimum" to minimumVersion
            ))
            _versionStatus.value = VersionStatus.Blocked(minimumVersion)
            VersionCheckResult.Blocked(minimumVersion)
        } else {
            UiLog.sys("VersionEnforcer", "VERSION_ALLOWED", mapOf(
                "current" to currentVersion,
                "minimum" to minimumVersion
            ))
            _versionStatus.value = VersionStatus.Allowed
            VersionCheckResult.Allowed
        }
    }

    private suspend fun fetchMinimumVersion(): String? {
        return try {
            val version = remoteConfigClient.getMinimumVersion()
            UiLog.sys("VersionEnforcer", "FETCH_SUCCESS", mapOf("minimumVersion" to version))
            cache.saveMinimumVersion(version)
            version
        } catch (e: Exception) {
            UiLog.err("VersionEnforcer", "FETCH_FAILED", e)
            val cached = cache.getMinimumVersion()
            if (cached != null) {
                UiLog.sys("VersionEnforcer", "USING_CACHED_VERSION", mapOf("cachedVersion" to cached))
            }
            cached
        }
    }
}

interface RemoteConfigClient {
    suspend fun getMinimumVersion(): String
}

interface VersionCache {
    fun saveMinimumVersion(version: String)
    fun getMinimumVersion(): String?
}

object VersionComparator {
    fun isLessThan(current: String, minimum: String): Boolean {
        val currentParts = current.split(".").map { it.toIntOrNull() ?: 0 }
        val minimumParts = minimum.split(".").map { it.toIntOrNull() ?: 0 }
        val maxLen = maxOf(currentParts.size, minimumParts.size)
        for (i in 0 until maxLen) {
            val c = currentParts.getOrElse(i) { 0 }
            val m = minimumParts.getOrElse(i) { 0 }
            if (c < m) return true
            if (c > m) return false
        }
        return false
    }

    fun isValidVersion(version: String): Boolean {
        return version.matches(Regex("\\d+(\\.\\d+)*"))
    }
}
