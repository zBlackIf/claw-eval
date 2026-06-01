package com.coni.hyperisle.overlay

import android.view.WindowManager
import java.util.function.Consumer
import com.coni.hyperisle.core.logging.UiLog

internal class OverlayScreenRecordingController(
    private val service: OverlayService,
    private val windowManager: WindowManager
) {
    private val TAG = "ScreenRecordCtrl"
    private var screenRecordingRegistered = false

    private val callback = Consumer<Int> { state ->
        if (state == WindowManager.ScreenRecordingCallback.STATE_VISIBLE) {
            UiLog.sys(TAG, "SCREEN_RECORDING_DETECTED")
            service.onScreenRecordingStateChanged(true)
        } else {
            service.onScreenRecordingStateChanged(false)
        }
    }

    fun register() {
        if (screenRecordingRegistered) return
        try {
            windowManager.addScreenRecordingCallback(service.mainExecutor, callback)
            screenRecordingRegistered = true
            UiLog.sys(TAG, "SCREEN_RECORDING_CALLBACK_REGISTERED")
        } catch (e: Exception) {
            UiLog.err(TAG, "Failed to register screen recording callback: ${e.message}")
        }
    }

    fun unregister() {
        if (!screenRecordingRegistered) return
        try {
            windowManager.removeScreenRecordingCallback(callback)
            UiLog.sys(TAG, "SCREEN_RECORDING_CALLBACK_UNREGISTERED")
        } catch (e: Exception) {
            UiLog.err(TAG, "Failed to unregister screen recording callback: ${e.message}")
        }
        screenRecordingRegistered = false
    }
}
