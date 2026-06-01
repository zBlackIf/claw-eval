#pragma once

#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace usslog {

struct StorageConfig {
    std::filesystem::path storage_directory;
    std::size_t max_file_size{10 * 1024 * 1024};  // 10 MB default
    std::size_t max_total_files{100};
    bool compression_enabled{true};
    std::string file_prefix{"ussdata"};
};

struct StorageStatistics {
    std::size_t current_file_size{0};
    std::size_t total_bytes_written{0};
    std::size_t file_count{0};
    std::size_t compressed_file_count{0};
    std::size_t files_deleted_by_retention{0};
};

class FileStorageManager {
public:
    explicit FileStorageManager(StorageConfig config);
    ~FileStorageManager();

    // Non-copyable, non-movable
    FileStorageManager(const FileStorageManager&) = delete;
    FileStorageManager& operator=(const FileStorageManager&) = delete;

    // Core operations
    bool Initialize();
    bool Write(const std::string& data);
    void Shutdown();

    // Statistics (public API - DO NOT CHANGE SIGNATURES)
    std::size_t GetCurrentFileSize() const;
    std::size_t GetTotalBytesWritten() const;
    std::size_t GetFileCount() const;
    std::size_t GetCompressedFileCount() const;
    std::size_t GetFilesDeletedByRetention() const;
    StorageStatistics GetStatistics() const;

private:
    // Internal methods to implement
    void StartupScan();
    bool RotateFile();
    bool CompressFile(const std::filesystem::path& source_path);
    bool ValidateCompressedFile(const std::filesystem::path& compressed_path,
                                 const std::filesystem::path& original_path);
    void EnforceRetentionPolicy();
    std::string GenerateFilename(std::uint32_t file_number) const;
    std::string GenerateTimestamp() const;

    StorageConfig m_config;
    std::filesystem::path m_current_file_path;
    std::uint32_t m_next_file_number{1};
    std::mutex m_write_mutex;

    // Atomic statistics
    std::atomic<std::size_t> m_current_file_size{0};
    std::atomic<std::size_t> m_total_bytes_written{0};
    std::atomic<std::size_t> m_file_count{0};
    std::atomic<std::size_t> m_compressed_file_count{0};
    std::atomic<std::size_t> m_files_deleted_by_retention{0};

    bool m_initialized{false};
    bool m_shutdown_requested{false};
};

}  // namespace usslog
