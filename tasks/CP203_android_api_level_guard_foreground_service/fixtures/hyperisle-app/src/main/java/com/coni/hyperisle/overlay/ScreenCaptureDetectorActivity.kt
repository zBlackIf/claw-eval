package com.coni.hyperisle.overlay

import android.app.Activity
import android.os.Bundle
import com.coni.hyperisle.core.logging.UiLog

/**
 * Activity that detects screen capture events and notifies the overlay system.
 * Uses API 34+ screen capture callback APIs.
 */
class ScreenCaptureDetectorActivity : Activity() {

    // BUG: registerScreenCaptureCallback requires API 34+. No guard present.
    // On Android 9 this will crash with NoSuchMethodError.
    private val screenCaptureCallback = Activity.ScreenCaptureCallback {
        UiLog.sys(TAG, "SCREEN_CAPTURE_DETECTED")
        handleScreenCapture()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // BUG: No API level check. This will crash on API < 34.
        registerScreenCaptureCallback(mainExecutor, screenCaptureCallback)
        UiLog.sys(TAG, "SCREEN_CAPTURE_CALLBACK_REGISTERED")
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterScreenCaptureCallback(screenCaptureCallback)
    }

    private fun handleScreenCapture() {
        UiLog.sys(TAG, "HANDLING_SCREEN_CAPTURE")
        // Notify overlay system about screen capture
        setResult(RESULT_OK)
        finish()
    }

    companion object {
        private const val TAG = "ScreenCaptureDetector"
    }
}
