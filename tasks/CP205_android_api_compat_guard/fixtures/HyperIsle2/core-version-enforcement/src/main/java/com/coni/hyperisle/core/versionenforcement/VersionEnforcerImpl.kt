package com.coni.hyperisle.core.versionenforcement

import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.core.network.RemoteConfigClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Production implementation of VersionEnforcer that fetches minimum version
 * from Firebase RemoteConfig and compares with installed app version.
 */
class VersionEnforcerImpl(
    private val remoteConfigClient: RemoteConfigClient,
    private val installedVersion: String,
    private val cache: VersionCache
) : VersionEnforcer {

    private val TAG = "VersionEnforcer"
    private val _versionStatus = MutableStateFlow(VersionStatus.Checking)
    override val versionStatus: StateFlow<VersionStatus> = _versionStatus.asStateFlow()

    override suspend fun checkVersion(): VersionCheckResult {
        _versionStatus.value = VersionStatus.Checking
        val minVersion = fetchMinimumVersion()
        return when {
            minVersion == null -> {
                _versionStatus.value = VersionStatus.Allowed
                VersionCheckResult.Allowed
            }
            compareVersions(installedVersion, minVersion) >= 0 -> {
                _versionStatus.value = VersionStatus.Allowed
                VersionCheckResult.Allowed
            }
            else -> {
                _versionStatus.value = VersionStatus.UpdateRequired
                cache.setMinimumVersion(minVersion)
                VersionCheckResult.UpdateRequired(minVersion)
            }
        }
    }

    private suspend fun fetchMinimumVersion(): String? {
        return try {
            remoteConfigClient.getString("min_app_version").takeIf { it.isNotEmpty() }
        } catch (e: Exception) {
            UiLog.err(TAG, "Failed to fetch minimum version: ${e.message}")
            null
        }
    }

    private fun compareVersions(installed: String, minimum: String): Int {
        val installedParts = installed.split(".").map { it.toIntOrNull() ?: 0 }
        val minimumParts = minimum.split(".").map { it.toIntOrNull() ?: 0 }
        val maxLen = maxOf(installedParts.size, minimumParts.size)
        for (i in 0 until maxLen) {
            val a = installedParts.getOrElse(i) { 0 }
            val b = minimumParts.getOrElse(i) { 0 }
            if (a != b) return a.compareTo(b)
        }
        return 0
    }
}

interface VersionCache {
    fun getMinimumVersion(): String?
    fun setMinimumVersion(version: String)
}
