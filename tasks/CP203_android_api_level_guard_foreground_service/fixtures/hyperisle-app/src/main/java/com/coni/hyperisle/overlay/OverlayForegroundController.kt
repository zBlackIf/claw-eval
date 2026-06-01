package com.coni.hyperisle.overlay

import android.app.Notification
import android.app.Service
import android.content.pm.ServiceInfo
import com.coni.hyperisle.core.logging.UiLog
import com.coni.hyperisle.notification.NotificationChannels
import com.coni.hyperisle.notification.NotificationFactory
import com.coni.hyperisle.notification.NotificationIds

internal class OverlayForegroundController(
    private val service: Service
) {
    private var lastGhostMode = false

    fun startForeground(ghostMode: Boolean) {
        UiLog.sys("OverlayService", "START_FOREGROUND_SERVICE", mapOf(
            "ghostMode" to ghostMode,
            "timestamp" to System.currentTimeMillis()
        ))

        NotificationChannels.createChannels(service)

        val notification = NotificationFactory
            .createOverlayServiceNotification(service, ghostMode)

        val notificationId = NotificationIds.OVERLAY_SERVICE

        // BUG: This uses FOREGROUND_SERVICE_TYPE_SPECIAL_USE which requires API 34+.
        // On Android 9 (API 28) devices this crashes with NoSuchFieldError.
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
        if (ghostMode == lastGhostMode) {
            return
        }

        val notificationId = NotificationIds.OVERLAY_SERVICE
        val notification = NotificationFactory
            .createOverlayServiceNotification(service, ghostMode)

        service.startForeground(
            notificationId,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        )
        lastGhostMode = ghostMode
    }

    companion object {
        private const val TAG = "OverlayForegroundController"
    }
}
