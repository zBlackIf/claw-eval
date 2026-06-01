package com.coni.hyperisle.core.versionenforcement

import android.content.Context
import android.content.SharedPreferences
import com.coni.hyperisle.core.logging.UiLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class VersionEnforcerImpl(
    private val context: Context,
    private val prefs: SharedPreferences
) : VersionEnforcer {

    override var versionStatus: VersionStatus = VersionStatus.Checking
        private set

    private val cache = VersionCache(prefs)

    // BUG: No timeout on Firebase fetch. If Firebase is slow or unreachable,
    // versionStatus stays as Checking forever, and the app appears frozen.
    override suspend fun checkVersion(): VersionCheckResult {
        return withContext(Dispatchers.IO) {
            try {
                val minVersion = fetchMinimumVersion()
                cache.saveMinimumVersion(minVersion)
                val currentVersion = getAppVersion()
                val result = compareVersions(currentVersion, minVersion)
                versionStatus = when (result) {
                    is VersionCheckResult.Allowed -> VersionStatus.Allowed
                    is VersionCheckResult.UpdateRequired -> VersionStatus.UpdateRequired
                    is VersionCheckResult.Blocked -> VersionStatus.Blocked
                    else -> VersionStatus.Allowed
                }
                result
            } catch (e: Exception) {
                UiLog.err(TAG, "VERSION_CHECK_FAILED", e)
                versionStatus = VersionStatus.Allowed
                VersionCheckResult.Error
            }
        }
    }

    private suspend fun fetchMinimumVersion(): String {
        // Simulates Firebase Remote Config fetch - can hang indefinitely
        // on poor network or when Firebase is unreachable
        return FirebaseVersionFetcher.fetchMinVersion()
    }

    private fun getAppVersion(): String {
        return context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: "0.0.0"
    }

    private fun compareVersions(current: String, minimum: String): VersionCheckResult {
        // Simple version comparison logic
        return if (current >= minimum) {
            VersionCheckResult.Allowed
        } else {
            VersionCheckResult.UpdateRequired(minimum)
        }
    }

    companion object {
        private const val TAG = "VersionEnforcer"
    }
}

internal class VersionCache(private val prefs: SharedPreferences) {
    fun saveMinimumVersion(version: String) {
        prefs.edit().putString(KEY_MIN_VERSION, version).apply()
    }

    fun getMinimumVersion(): String? {
        return prefs.getString(KEY_MIN_VERSION, null)
    }

    companion object {
        private const val KEY_MIN_VERSION = "min_version_cached"
    }
}

internal object FirebaseVersionFetcher {
    suspend fun fetchMinVersion(): String {
        // Firebase Remote Config fetch - no timeout applied
        TODO("Firebase fetch implementation")
    }
}
