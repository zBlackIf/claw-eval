package com.coni.hyperisle.overlay

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import com.coni.hyperisle.core.logging.UiLog

internal class OverlayForegroundController(
    private val service: OverlayService
) {
    private val TAG = "OverlayFgCtrl"
    private val CHANNEL_ID = "overlay_service_channel"
    private val NOTIFICATION_ID = 1001

    fun startForeground() {
        createNotificationChannel()
        val notification = buildNotification()
        service.startForeground(
            NOTIFICATION_ID,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        )
        UiLog.sys(TAG, "FOREGROUND_STARTED")
    }

    fun stopForeground() {
        service.stopForeground(true)
        UiLog.sys(TAG, "FOREGROUND_STOPPED")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Overlay Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = service.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(service, CHANNEL_ID)
            .setContentTitle("HyperIsle Active")
            .setContentText("Overlay service is running")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
}
