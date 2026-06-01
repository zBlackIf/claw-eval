/**
 * @file logger.h
 * @brief Unified logging interface for DEV_ENV builds
 *
 * In development environment, this provides printf-style logging macros.
 * In production (non-DEV_ENV), code uses SocMwLog.h system logging.
 */

#pragma once

#include <cstdio>
#include <cstdarg>

// Development environment logging implementation
#define LOG_INFO(tag, fmt, ...)  \
    printf("[INFO][%s] " fmt "\n", tag, ##__VA_ARGS__)

#define LOG_DEBUG(tag, fmt, ...) \
    printf("[DEBUG][%s] " fmt "\n", tag, ##__VA_ARGS__)

#define LOG_WARN(tag, fmt, ...)  \
    printf("[WARN][%s] " fmt "\n", tag, ##__VA_ARGS__)

#define LOG_ERROR(tag, fmt, ...) \
    printf("[ERROR][%s] " fmt "\n", tag, ##__VA_ARGS__)
