/**
 * @file clone_manager.cpp
 * @brief Example file showing htvclone's logging pattern (reference for unification)
 */

#include "clone_types.h"

#define TAG "CloneManager"

namespace CloneManagerMw {

void CloneManager::init() {
    LOG_INFO(TAG, "CloneManager initialized");
}

void CloneManager::startClone(const std::string& source) {
    LOG_INFO(TAG, "Starting clone from source: %s", source.c_str());
    LOG_DEBUG(TAG, "Clone parameters validated");
}

void CloneManager::handleError(int code) {
    LOG_ERROR(TAG, "Clone error occurred, code=%d", code);
}

} // namespace CloneManagerMw
