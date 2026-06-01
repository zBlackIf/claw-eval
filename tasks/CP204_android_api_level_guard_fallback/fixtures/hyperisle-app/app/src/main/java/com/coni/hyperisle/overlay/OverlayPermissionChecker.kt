package com.coni.hyperisle.overlay

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import com.coni.hyperisle.core.logging.UiLog

/**
 * Checks and requests overlay (draw over other apps) permission.
 */
object OverlayPermissionChecker {

    fun hasPermission(context: Context): Boolean {
        return Settings.canDrawOverlays(context)
    }

    // BUG: Only uses standard ACTION_MANAGE_OVERLAY_PERMISSION intent.
    // On Huawei EMUI, this intent doesn't open the correct settings page.
    // Needs a Huawei-specific fallback chain.
    fun settingsIntent(context: Context): Intent {
        return Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${context.packageName}")
        )
    }
}
