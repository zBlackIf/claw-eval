// TODO: Implement FileStorageManager
// This file needs a complete implementation following the log rotation patterns.
// See include/file_storage_manager.h for the interface definition.

#include "file_storage_manager.h"

namespace usslog {

FileStorageManager::FileStorageManager(StorageConfig config)
    : m_config(std::move(config)) {}

FileStorageManager::~FileStorageManager() {
    Shutdown();
}

// TODO: Implement all methods declared in the header

}  // namespace usslog
