package com.coni.hyperisle.app

import android.app.Application
import android.util.Log
import com.coni.hyperisle.prefs.SecurePrefsManager
import com.coni.hyperisle.version.VersionEnforcer
import com.coni.hyperisle.version.VersionEnforcerImpl

class HyperIsleApp : Application() {

    lateinit var versionEnforcer: VersionEnforcer
    lateinit var featureFlagRepository: FeatureFlagRepository
    lateinit var premiumGate: PremiumGate

    override fun onCreate() {
        super.onCreate()
        initializeFeatureControl()
    }

    private fun initializeFeatureControl() {
        try {
            val prefs = SecurePrefsManager.createEncryptedPrefs(this)
            versionEnforcer = VersionEnforcerImpl(prefs)
            featureFlagRepository = FeatureFlagRepositoryImpl(prefs)
            premiumGate = PremiumGateImpl(prefs)
        } catch (e: Exception) {
            Log.e("HyperIsleApp", "Failed to initialize feature control", e)
            // If this fails, lateinit fields remain uninitialized
            // causing UninitializedPropertyAccessException in MainActivity
        }
    }
}

interface FeatureFlagRepository {
    fun isEnabled(flag: String): Boolean
}

class FeatureFlagRepositoryImpl(
    private val prefs: android.content.SharedPreferences
) : FeatureFlagRepository {
    override fun isEnabled(flag: String): Boolean {
        return prefs.getBoolean(flag, false)
    }
}

interface PremiumGate {
    fun isPremium(): Boolean
}

class PremiumGateImpl(
    private val prefs: android.content.SharedPreferences
) : PremiumGate {
    override fun isPremium(): Boolean {
        return prefs.getBoolean("premium_active", false)
    }
}
