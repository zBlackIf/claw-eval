package com.coni.hyperisle.overlay

import android.app.Activity
import android.os.Build

/**
 * Detects screen recording using Android 14+ APIs.
 * BUG: No API version guard — crashes on Android 9 with NoSuchMethodError.
 */
class OverlayScreenRecordingController(private val activity: Activity) {

    private var isMonitoring = false

    fun startMonitoring() {
        isMonitoring = true
        // Uses registerScreenCaptureCallback which is API 34+ only
        // No version check present — will crash on API < 34
        activity.registerScreenCaptureCallback(
            activity.mainExecutor
        ) {
            onScreenCaptureDetected()
        }
    }

    fun stopMonitoring() {
        isMonitoring = false
    }

    private fun onScreenCaptureDetected() {
        // Handle screen capture event
    }
}
