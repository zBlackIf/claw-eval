package com.coni.hyperisle.overlay

import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import com.coni.hyperisle.core.logging.UiLog

/**
 * Detects screen capture events and notifies the overlay system.
 * Uses Activity.ScreenCaptureCallback API introduced in API 34.
 */
class ScreenCaptureDetectorActivity : Activity() {

    private var screenCaptureCallback: Activity.ScreenCaptureCallback? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        UiLog.sys("ScreenCaptureDetector", "ACTIVITY_CREATED")

        // BUG: No API level check. Activity.ScreenCaptureCallback requires API 34+.
        // On Android 9 (API 28) this causes NoSuchMethodError at runtime.
        screenCaptureCallback = Activity.ScreenCaptureCallback {
            UiLog.sys("ScreenCaptureDetector", "CAPTURE_DETECTED")
            handleScreenCapture()
        }

        registerScreenCaptureCallback(mainExecutor, screenCaptureCallback!!)
    }

    override fun onDestroy() {
        screenCaptureCallback?.let {
            unregisterScreenCaptureCallback(it)
        }
        super.onDestroy()
    }

    private fun handleScreenCapture() {
        UiLog.sys("ScreenCaptureDetector", "HANDLING_CAPTURE_EVENT")
        // Notify overlay system about capture
        OverlayEventBus.postScreenCaptureEvent()
    }
}
