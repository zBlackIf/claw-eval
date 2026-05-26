package com.orientdb.studio.config;

public class SecurityConfig {
    // Authentication required for admin endpoints
    public static final boolean AUTH_REQUIRED = true;
    // MISSING: No file upload security configuration
    // MISSING: No CSRF protection for upload endpoints
    // MISSING: No Content-Security-Policy headers
    // MISSING: No file extension whitelist

    public static final String[] ALLOWED_ROLES = {"admin", "writer"};

    public static boolean isAuthorized(String role) {
        for (String allowed : ALLOWED_ROLES) {
            if (allowed.equals(role)) return true;
        }
        return false;
    }
}
