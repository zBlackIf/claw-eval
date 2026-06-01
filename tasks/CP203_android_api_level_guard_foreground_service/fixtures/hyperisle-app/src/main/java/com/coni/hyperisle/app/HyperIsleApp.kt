package com.coni.hyperisle.app

import android.app.Application
import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.core.versionenforcement.VersionEnforcer
import com.coni.hyperisle.core.versionenforcement.VersionEnforcerImpl
import com.coni.hyperisle.core.featureflags.FeatureFlagRepository
import com.coni.hyperisle.core.featureflags.FeatureFlagRepositoryImpl
import com.coni.hyperisle.core.premium.PremiumGate
import com.coni.hyperisle.core.premium.PremiumGateImpl

class HyperIsleApp : Application() {

    // BUG: lateinit will crash with UninitializedPropertyAccessException if
    // initializeFeatureControl() throws (e.g., Huawei KeyStore exception).
    // MainActivity and other components access these directly.
    lateinit var versionEnforcer: VersionEnforcer
        private set
    lateinit var featureFlagRepository: FeatureFlagRepository
        private set
    lateinit var premiumGate: PremiumGate
        private set

    override fun onCreate() {
        super.onCreate()
        initializeFeatureControl()
    }

    private fun initializeFeatureControl() {
        try {
            val encryptedPrefs = createEncryptedPrefs()
            versionEnforcer = VersionEnforcerImpl(this, encryptedPrefs)
            featureFlagRepository = FeatureFlagRepositoryImpl(encryptedPrefs)
            premiumGate = PremiumGateImpl(encryptedPrefs)
            UiLog.sys(TAG, "FEATURE_CONTROL_INITIALIZED")
        } catch (e: Exception) {
            // BUG: If exception occurs (common on Huawei EMUI + Android 9),
            // lateinit vars remain uninitialized. App will crash later when
            // MainActivity accesses them.
            UiLog.err(TAG, "FEATURE_CONTROL_INIT_FAILED", e)
        }
    }

    private fun createEncryptedPrefs(): android.content.SharedPreferences {
        // BUG: No fallback if EncryptedSharedPreferences fails.
        // On Huawei EMUI + Android 9, MasterKey generation often throws
        // KeyStoreException. Should have retry + plain SharedPreferences fallback.
        val masterKey = androidx.security.crypto.MasterKey.Builder(this)
            .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM)
            .build()

        return androidx.security.crypto.EncryptedSharedPreferences.create(
            this,
            "hyperisle_feature_control",
            masterKey,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    companion object {
        private const val TAG = "HyperIsleApp"
    }
}
