package com.coni.hyperisle.overlay

import android.content.Context
import com.coni.hyperisle.core.logging.UiLog

/**
 * Controller for detecting screen recording state.
 * Uses API 34+ WindowManager screen recording detection APIs.
 */
class OverlayScreenRecordingController(
    private val context: Context
) {
    private var isMonitoring = false

    // BUG: No API level guard. addScreenRecordingCallback requires API 34+.
    fun startMonitoring() {
        if (isMonitoring) return
        val windowManager = context.getSystemService(Context.WINDOW_SERVICE)
            as android.view.WindowManager
        windowManager.addScreenRecordingCallback(context.mainExecutor) { state ->
            handleRecordingStateChange(state)
        }
        isMonitoring = true
        UiLog.sys(TAG, "SCREEN_RECORDING_MONITORING_STARTED")
    }

    fun stopMonitoring() {
        if (!isMonitoring) return
        isMonitoring = false
        UiLog.sys(TAG, "SCREEN_RECORDING_MONITORING_STOPPED")
    }

    private fun handleRecordingStateChange(state: Int) {
        UiLog.sys(TAG, "RECORDING_STATE_CHANGED", mapOf("state" to state))
    }

    companion object {
        private const val TAG = "ScreenRecordingCtrl"
    }
}
