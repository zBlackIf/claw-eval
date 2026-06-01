package com.coni.hyperisle.version

import android.content.SharedPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

enum class VersionStatus {
    Checking, Allowed, UpdateRequired, Blocked
}

data class VersionCheckResult(
    val status: VersionStatus,
    val message: String? = null
) {
    companion object {
        val Allowed = VersionCheckResult(VersionStatus.Allowed)
    }
}

interface VersionEnforcer {
    val versionStatus: VersionStatus
    suspend fun checkVersion(): VersionCheckResult
}

class VersionEnforcerImpl(
    private val prefs: SharedPreferences
) : VersionEnforcer {

    override var versionStatus: VersionStatus = VersionStatus.Checking
        private set

    override suspend fun checkVersion(): VersionCheckResult {
        versionStatus = VersionStatus.Checking
        val minVersion = fetchMinimumVersion()
        val currentVersion = getCurrentVersion()
        return if (currentVersion >= minVersion) {
            versionStatus = VersionStatus.Allowed
            VersionCheckResult.Allowed
        } else {
            versionStatus = VersionStatus.UpdateRequired
            VersionCheckResult(VersionStatus.UpdateRequired, "Please update to version $minVersion")
        }
    }

    private suspend fun fetchMinimumVersion(): Int {
        // Fetches from Firebase Remote Config - no timeout protection
        return withContext(Dispatchers.IO) {
            // Simulates Firebase call that can hang on slow networks
            val cached = prefs.getInt("cached_min_version", 1)
            cached
        }
    }

    private fun getCurrentVersion(): Int {
        return prefs.getInt("current_version", 100)
    }
}
