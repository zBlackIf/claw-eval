#ifndef LOGGER_H
#define LOGGER_H

#include <cstdio>
#include <string>

#define LOG_INFO(tag, fmt, ...) printf("[INFO][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define LOG_ERROR(tag, fmt, ...) fprintf(stderr, "[ERROR][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define LOG_WARN(tag, fmt, ...) fprintf(stderr, "[WARN][%s] " fmt "\n", tag, ##__VA_ARGS__)

#endif // LOGGER_H
