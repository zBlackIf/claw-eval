package com.coni.hyperisle.overlay

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
import android.view.WindowManager
import com.coni.hyperisle.core.logging.UiLog

/**
 * Invisible "ghost" Activity that runs in the background to detect screenshots
 * using Android 14+ ScreenCaptureCallback API.
 */
class ScreenCaptureDetectorActivity : Activity() {

    private val TAG = "ScreenCaptureDetector"
    private var screenCaptureCallback: Activity.ScreenCaptureCallback? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE)
        window.addFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE)

        screenCaptureCallback = Activity.ScreenCaptureCallback {
            UiLog.sys(TAG, "SCREEN_CAPTURE_DETECTED")
            sendBroadcast(Intent("com.coni.hyperisle.SCREEN_CAPTURED"))
        }
        registerScreenCaptureCallback(mainExecutor, screenCaptureCallback!!)
        UiLog.sys(TAG, "SCREEN_CAPTURE_CALLBACK_REGISTERED")
    }

    override fun onDestroy() {
        screenCaptureCallback?.let { unregisterScreenCaptureCallback(it) }
        super.onDestroy()
    }
}
