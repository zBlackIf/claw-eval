package com.coni.hyperisle.app

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.coni.hyperisle.core.billing.PremiumGate
import com.coni.hyperisle.core.billing.PremiumStatusRepository
import com.coni.hyperisle.core.featureflags.FeatureFlagRepository
import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.core.versionenforcement.VersionEnforcer
import com.coni.hyperisle.app.featurecontrol.FeatureControlModule
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.security.KeyStore

class HyperIsleApp : Application() {

    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    // BUG: These are lateinit vars. If initializeFeatureControl() throws an exception
    // (e.g., Huawei KeyStore error), these remain uninitialized.
    // When MainActivity accesses them, UninitializedPropertyAccessException crashes the app.
    lateinit var versionEnforcer: VersionEnforcer
        private set
    lateinit var featureFlagRepository: FeatureFlagRepository
        private set
    lateinit var premiumStatusRepository: PremiumStatusRepository
        private set
    lateinit var premiumGate: PremiumGate
        private set

    override fun onCreate() {
        super.onCreate()
        UiLog.sys("HyperIsleApp", "APP_CREATED")

        initializeFeatureControl()

        applicationScope.launch {
            initializeFeatureControlAsync()
        }
    }

    private fun initializeFeatureControl() {
        UiLog.sys("HyperIsleApp", "FEATURE_CONTROL_INIT_START")

        try {
            // BUG: On Huawei Android 9 devices, EncryptedSharedPreferences throws
            // a KeyStore exception. This causes the entire try block to fail,
            // leaving all lateinit vars uninitialized.
            val encryptedPrefs = createEncryptedPrefs()

            val remoteConfigClient = FeatureControlModule.provideRemoteConfigClient()
            val versionCache = FeatureControlModule.provideVersionCache(encryptedPrefs)
            val featureFlagCache = FeatureControlModule.provideFeatureFlagCache(encryptedPrefs)

            versionEnforcer = FeatureControlModule.provideVersionEnforcer(
                remoteConfigClient, versionCache
            )
            featureFlagRepository = FeatureControlModule.provideFeatureFlagRepository(
                remoteConfigClient, featureFlagCache
            )
            premiumStatusRepository = FeatureControlModule.providePremiumStatusRepository()
            premiumGate = FeatureControlModule.providePremiumGate(premiumStatusRepository)

            UiLog.sys("HyperIsleApp", "FEATURE_CONTROL_INIT_SUCCESS")
        } catch (e: Exception) {
            UiLog.err("HyperIsleApp", "FEATURE_CONTROL_INIT_FAILED", e)
            // BUG: No fallback assignment. lateinit vars remain uninitialized.
        }
    }

    private suspend fun initializeFeatureControlAsync() {
        try {
            // BUG: No timeout. If Firebase is unreachable, this hangs indefinitely.
            versionEnforcer.checkVersion(getAppVersionName())
        } catch (e: Exception) {
            UiLog.err("HyperIsleApp", "VERSION_CHECK_FAILED", e)
        }
    }

    // BUG: No fallback if KeyStore/EncryptedSharedPreferences fails on Huawei.
    private fun createEncryptedPrefs(): SharedPreferences {
        val masterKey = MasterKey.Builder(this)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        return EncryptedSharedPreferences.create(
            this,
            "hyperisle_feature_control",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    private fun deleteFeatureControlMasterKey() {
        try {
            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            keyStore.deleteEntry("_androidx_security_master_key_")
        } catch (e: Exception) {
            UiLog.err("HyperIsleApp", "DELETE_MASTER_KEY_FAILED", e)
        }
    }

    private fun getAppVersionName(): String {
        return try {
            packageManager.getPackageInfo(packageName, 0).versionName ?: "0.0.0"
        } catch (e: Exception) {
            "0.0.0"
        }
    }
}
