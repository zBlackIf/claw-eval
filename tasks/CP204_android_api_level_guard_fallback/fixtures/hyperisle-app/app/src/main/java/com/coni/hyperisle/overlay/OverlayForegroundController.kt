package com.coni.hyperisle.overlay

import android.app.Notification
import android.app.Service
import android.content.pm.ServiceInfo
import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.notification.NotificationChannels
import com.coni.hyperisle.notification.NotificationFactory
import com.coni.hyperisle.notification.NotificationIds

internal class OverlayForegroundController(
    private val service: OverlayService
) {
    private var lastGhostMode = false

    companion object {
        private const val TAG = "OverlayForegroundCtrl"
    }

    fun startForeground(ghostMode: Boolean) {
        UiLog.sys("OverlayService", "START_FOREGROUND_SERVICE", mapOf(
            "ghostMode" to ghostMode,
            "timestamp" to System.currentTimeMillis()
        ))

        NotificationChannels.createChannels(service)

        UiLog.sys(TAG, "CREATE_FOREGROUND_NOTIFICATION")
        val notification = NotificationFactory
            .createOverlayServiceNotification(service, ghostMode)

        val notificationId = NotificationIds.OVERLAY_SERVICE

        // BUG: This unconditionally uses FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        // which is only available on API 34+. On Android 9 (API 28) this crashes
        // with IllegalArgumentException because the service type constant doesn't exist.
        service.startForeground(
            notificationId,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        )
        lastGhostMode = ghostMode

        UiLog.sys("OverlayService", "START_FOREGROUND_COMPLETE", mapOf(
            "ghostMode" to ghostMode,
            "success" to true
        ))
    }

    fun updateForegroundNotification(ghostMode: Boolean) {
        if (ghostMode == lastGhostMode) return

        val notification = NotificationFactory
            .createOverlayServiceNotification(service, ghostMode)
        val notificationId = NotificationIds.OVERLAY_SERVICE

        service.startForeground(
            notificationId,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        )
        lastGhostMode = ghostMode
    }
}
