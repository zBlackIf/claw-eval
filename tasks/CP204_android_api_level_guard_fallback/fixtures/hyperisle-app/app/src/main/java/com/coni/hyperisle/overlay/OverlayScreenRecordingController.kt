package com.coni.hyperisle.overlay

import android.app.Activity
import android.os.Build
import com.coni.hyperisle.core.logging.UiLog

/**
 * Monitors screen recording state and alerts the user if recording is detected.
 * Uses Activity.registerScreenCaptureCallback (API 34+).
 */
class OverlayScreenRecordingController(
    private val activity: Activity
) {
    private var isMonitoring = false

    // BUG: No API level check. registerScreenCaptureCallback requires API 34+.
    // On Android 9 (API 28) this causes NoSuchMethodError.
    fun startMonitoring() {
        if (isMonitoring) return
        UiLog.sys("ScreenRecording", "START_MONITORING")

        activity.registerScreenCaptureCallback(activity.mainExecutor) {
            UiLog.sys("ScreenRecording", "RECORDING_DETECTED")
            onRecordingDetected()
        }
        isMonitoring = true
    }

    fun stopMonitoring() {
        if (!isMonitoring) return
        UiLog.sys("ScreenRecording", "STOP_MONITORING")
        // Cannot unregister without reference - this is also a bug
        isMonitoring = false
    }

    private fun onRecordingDetected() {
        UiLog.sys("ScreenRecording", "ALERTING_USER")
        // Show warning overlay
    }
}
