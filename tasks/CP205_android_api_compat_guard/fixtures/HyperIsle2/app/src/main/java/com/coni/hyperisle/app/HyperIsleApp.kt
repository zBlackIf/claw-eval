package com.coni.hyperisle.app

import android.app.Application
import android.content.Context
import androidx.lifecycle.ProcessLifecycleOwner
import com.coni.hyperisle.core.billing.PremiumGate
import com.coni.hyperisle.core.billing.PremiumStatusRepository
import com.coni.hyperisle.core.featureflags.FeatureFlagRepository
import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.core.versionenforcement.VersionEnforcer
import com.coni.hyperisle.core.versionenforcement.VersionEnforcerImpl
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class HyperIsleApp : Application() {

    private val TAG = "HyperIsleApp"
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    lateinit var versionEnforcer: VersionEnforcer
        private set

    lateinit var featureFlagRepository: FeatureFlagRepository
        private set

    lateinit var premiumGate: PremiumGate
        private set

    lateinit var premiumStatusRepository: PremiumStatusRepository
        private set

    override fun onCreate() {
        super.onCreate()
        initializeLogging()
        initializeFeatureControl()
        initializeFeatureControlAsync()
    }

    private fun initializeLogging() {
        UiLog.init(this)
    }

    private fun initializeFeatureControl() {
        val encryptedPrefs = createEncryptedPrefs()
        featureFlagRepository = createFeatureFlagRepository(encryptedPrefs)
        premiumGate = createPremiumGate()
        premiumStatusRepository = createPremiumStatusRepository()
        versionEnforcer = createVersionEnforcer()
    }

    private fun initializeFeatureControlAsync() {
        applicationScope.launch {
            versionEnforcer.checkVersion()
        }
    }

    private fun createEncryptedPrefs(): android.content.SharedPreferences {
        val masterKey = androidx.security.crypto.MasterKey.Builder(this)
            .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM)
            .build()
        return androidx.security.crypto.EncryptedSharedPreferences.create(
            this,
            "feature_control_prefs",
            masterKey,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    private fun createFeatureFlagRepository(prefs: android.content.SharedPreferences): FeatureFlagRepository {
        // Simplified: real impl uses RemoteConfigClient
        throw NotImplementedError("Stub for eval")
    }

    private fun createPremiumGate(): PremiumGate {
        throw NotImplementedError("Stub for eval")
    }

    private fun createPremiumStatusRepository(): PremiumStatusRepository {
        throw NotImplementedError("Stub for eval")
    }

    private fun createVersionEnforcer(): VersionEnforcer {
        throw NotImplementedError("Stub for eval")
    }
}
