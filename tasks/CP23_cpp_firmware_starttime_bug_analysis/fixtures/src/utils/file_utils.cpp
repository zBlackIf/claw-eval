#include "file_utils.h"
#include "logger.h"
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#include <unistd.h>
#include <fcntl.h>
#include <cstring>
#include <algorithm>

#define LOG_TAG "FileUtils"

namespace CloneMgrMw {

bool FileUtils::fileExists(const std::string& path) {
    struct stat buffer;
    return (stat(path.c_str(), &buffer) == 0);
}

bool FileUtils::directoryExists(const std::string& path) {
    struct stat buffer;
    if (stat(path.c_str(), &buffer) == 0) {
        return S_ISDIR(buffer.st_mode);
    }
    return false;
}

bool FileUtils::createDirectory(const std::string& path) {
    if (directoryExists(path)) {
        return true;
    }
    
    // 创建父目录
    size_t pos = path.find_last_of('/');
    if (pos != std::string::npos) {
        std::string parent = path.substr(0, pos);
        if (!parent.empty() && !createDirectory(parent)) {
            return false;
        }
    }
    
    // 创建当前目录
    int result = mkdir(path.c_str(), 0755);
    if (result != 0 && errno != EEXIST) {
        LOG_ERROR(LOG_TAG, "Failed to create directory: %s, error: %s", 
                 path.c_str(), strerror(errno));
        return false;
    }
    
    return true;
}

bool FileUtils::copyFile(const std::string& src, const std::string& dst) {
    if (!fileExists(src)) {
        LOG_ERROR(LOG_TAG, "Source file does not exist: %s", src.c_str());
        return false;
    }
    
    // 处理目标路径：如果目标是目录，则添加源文件名
    std::string finalDst = dst;
    if (directoryExists(dst)) {
        // 从源路径中提取文件名
        size_t srcPos = src.find_last_of('/');
        if (srcPos != std::string::npos) {
            std::string filename = src.substr(srcPos + 1);
            if (finalDst.back() != '/') {
                finalDst += '/';
            }
            finalDst += filename;
        }
    }
    
    // 确保目标目录存在
    size_t pos = finalDst.find_last_of('/');
    if (pos != std::string::npos) {
        std::string dir = finalDst.substr(0, pos);
        if (!createDirectory(dir)) {
            LOG_ERROR(LOG_TAG, "Failed to create destination directory: %s", dir.c_str());
            return false;
        }
    }
    
    int src_fd = open(src.c_str(), O_RDONLY);
    if (src_fd < 0) {
        LOG_ERROR(LOG_TAG, "Failed to open source file: %s, error: %s", 
                 src.c_str(), strerror(errno));
        return false;
    }
    
    int dst_fd = open(finalDst.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (dst_fd < 0) {
        LOG_ERROR(LOG_TAG, "Failed to create destination file: %s, error: %s", 
                 finalDst.c_str(), strerror(errno));
        close(src_fd);
        return false;
    }
    
    char buffer[4096];
    ssize_t bytes_read;
    bool success = true;
    
    while ((bytes_read = read(src_fd, buffer, sizeof(buffer))) > 0) {
        if (write(dst_fd, buffer, bytes_read) != bytes_read) {
            LOG_ERROR(LOG_TAG, "Failed to write to destination file: %s, error: %s", 
                     finalDst.c_str(), strerror(errno));
            success = false;
            break;
        }
    }
    
    if (bytes_read < 0) {
        LOG_ERROR(LOG_TAG, "Failed to read from source file: %s, error: %s", 
                 src.c_str(), strerror(errno));
        success = false;
    }
    
    close(src_fd);
    close(dst_fd);
    
    if (success) {
        LOG_INFO(LOG_TAG, "Copied file: %s -> %s", src.c_str(), finalDst.c_str());
    }
    
    return success;
}

bool FileUtils::copyDirectory(const std::string& src, const std::string& dst) {
    if (!directoryExists(src)) {
        LOG_ERROR(LOG_TAG, "Source directory does not exist: %s", src.c_str());
        return false;
    }
    
    // 创建目标目录
    if (!createDirectory(dst)) {
        LOG_ERROR(LOG_TAG, "Failed to create destination directory: %s", dst.c_str());
        return false;
    }
    
    DIR* dir = opendir(src.c_str());
    if (!dir) {
        LOG_ERROR(LOG_TAG, "Failed to open source directory: %s, error: %s", 
                 src.c_str(), strerror(errno));
        return false;
    }
    
    struct dirent* entry;
    bool success = true;
    
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        
        // 跳过 . 和 ..
        if (name == "." || name == "..") {
            continue;
        }
        
        // 构建源路径和目标路径，避免双斜杠问题
        std::string srcPath = src;
        std::string dstPath = dst;
        
        // 如果路径不以 '/' 结尾，则添加 '/'
        if (!srcPath.empty() && srcPath.back() != '/') {
            srcPath += '/';
        }
        if (!dstPath.empty() && dstPath.back() != '/') {
            dstPath += '/';
        }
        
        srcPath += name;
        dstPath += name;
        
        struct stat statbuf;
        if (lstat(srcPath.c_str(), &statbuf) != 0) {
            LOG_ERROR(LOG_TAG, "Failed to stat: %s, error: %s", 
                     srcPath.c_str(), strerror(errno));
            success = false;
            continue;
        }
        
        if (S_ISDIR(statbuf.st_mode)) {
            // 递归拷贝子目录
            if (!copyDirectory(srcPath, dstPath)) {
                success = false;
            }
        } else if (S_ISREG(statbuf.st_mode)) {
            // 拷贝文件
            if (!copyFile(srcPath, dstPath)) {
                success = false;
            }
        }
        // 忽略符号链接和其他特殊文件
    }
    
    closedir(dir);
    return success;
}

std::vector<std::string> FileUtils::listFiles(const std::string& path) {
    std::vector<std::string> files;
    
    DIR* dir = opendir(path.c_str());
    if (!dir) {
        return files;
    }
    
    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        
        // 跳过 . 和 ..
        if (name == "." || name == "..") {
            continue;
        }
        
        files.push_back(name);
    }
    
    closedir(dir);
    return files;
}

bool FileUtils::checkAllFilesExist(const std::string& directory, const std::vector<std::string>& files) {
    for (const auto& file : files) {
        // 构建完整路径，避免双斜杠问题
        std::string fullPath = directory;
        
        // 如果路径不以 '/' 结尾，则添加 '/'
        if (!fullPath.empty() && fullPath.back() != '/') {
            fullPath += '/';
        }
        
        fullPath += file;
        
        if (!fileExists(fullPath)) {
            LOG_WARN(LOG_TAG, "File not found: %s", fullPath.c_str());
            return false;
        }
    }
    return true;
}

bool FileUtils::copyFiles(const std::string& srcDir, const std::string& dstDir, 
                         const std::vector<std::string>& files) {
    // 确保目标目录存在
    if (!createDirectory(dstDir)) {
        LOG_ERROR(LOG_TAG, "Failed to create destination directory: %s", dstDir.c_str());
        return false;
    }
    
    bool success = true;
    for (const auto& file : files) {
        // 构建源路径和目标路径，避免双斜杠问题
        std::string srcPath = srcDir;
        std::string dstPath = dstDir;
        
        // 如果路径不以 '/' 结尾，则添加 '/'
        if (!srcPath.empty() && srcPath.back() != '/') {
            srcPath += '/';
        }
        if (!dstPath.empty() && dstPath.back() != '/') {
            dstPath += '/';
        }
        
        srcPath += file;
        dstPath += file;
        
        // 检查是否为目录
        if (directoryExists(srcPath)) {
            // 递归拷贝目录及其所有内容
            LOG_INFO(LOG_TAG, "Copying directory: %s -> %s", srcPath.c_str(), dstPath.c_str());
            if (!copyDirectory(srcPath, dstPath)) {
                LOG_ERROR(LOG_TAG, "Failed to copy directory: %s -> %s", 
                         srcPath.c_str(), dstPath.c_str());
                success = false;
            }
        } 
        // 检查是否为文件
        else if (fileExists(srcPath)) {
            // 拷贝单个文件
            if (!copyFile(srcPath, dstPath)) {
                LOG_ERROR(LOG_TAG, "Failed to copy file: %s -> %s", 
                         srcPath.c_str(), dstPath.c_str());
                success = false;
            }
        } 
        // 文件或目录都不存在
        else {
            LOG_ERROR(LOG_TAG, "Source does not exist (file or directory): %s", 
                     srcPath.c_str());
            success = false;
        }
    }
    
    return success;
}

long FileUtils::getFileSize(const std::string& path) {
    struct stat buffer;
    if (stat(path.c_str(), &buffer) == 0) {
        return buffer.st_size;
    }
    return -1;
}

time_t FileUtils::getFileModTime(const std::string& path) {
    struct stat buffer;
    if (stat(path.c_str(), &buffer) == 0) {
        return buffer.st_mtime;
    }
    return 0;
}

std::string FileUtils::getFormatTypeFromFile(const std::string& filePath) {
    // 查找最后一个点号的位置
    size_t dotPos = filePath.find_last_of('.');
    if (dotPos == std::string::npos) {
        // 没有扩展名，默认使用XML
        LOG_WARN(LOG_TAG, "No file extension found, defaulting to XML: %s", filePath.c_str());
        return "XML";
    }
    
    // 提取扩展名（不包含点号）
    std::string extension = filePath.substr(dotPos + 1);
    
    // 转换为大写进行比较
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char c) { return std::toupper(c); });
    
    // 根据扩展名返回格式类型
    if (extension == "XML") {
        return "XML";
    } else if (extension == "JSON") {
        return "JSON";
    } else {
        // 不支持的文件格式，默认使用XML
        LOG_WARN(LOG_TAG, "Unsupported file extension '%s', defaulting to XML: %s", 
                 extension.c_str(), filePath.c_str());
        return "XML";
    }
}

bool FileUtils::deleteFile(const std::string& path) {
    if (!fileExists(path)) {
        LOG_WARN(LOG_TAG, "File does not exist, nothing to delete: %s", path.c_str());
        return true;  // 文件不存在，视为删除成功
    }
    
    int result = unlink(path.c_str());
    if (result != 0) {
        LOG_ERROR(LOG_TAG, "Failed to delete file: %s, error: %s", 
                 path.c_str(), strerror(errno));
        return false;
    }
    
    LOG_INFO(LOG_TAG, "Deleted file: %s", path.c_str());
    return true;
}

bool FileUtils::unzipFile(const std::string& zipPath, const std::string& destPath) {
    // 检查 zip 文件是否存在
    if (!fileExists(zipPath)) {
        LOG_ERROR(LOG_TAG, "Zip file does not exist: %s", zipPath.c_str());
        return false;
    }
    
    // 确保目标目录存在
    if (!createDirectory(destPath)) {
        LOG_ERROR(LOG_TAG, "Failed to create destination directory: %s", destPath.c_str());
        return false;
    }
    
    // 构建 unzip 命令
    std::string command = "unzip -o \"" + zipPath + "\" -d \"" + destPath + "\"";
    
    LOG_INFO(LOG_TAG, "Executing unzip command: %s", command.c_str());
    
    // Run unzip command and read output line by line, Only for debug
    #ifdef FILE_DEBUG
        FILE* pipe = popen(command.c_str(), "r");
        if (!pipe) {
            LOG_ERROR(LOG_TAG, "Failed to execute unzip command, popen() error: %s", 
                    strerror(errno));
            return false;
        }
    

        char buffer[128];
        std::string output = "";
        while (!feof(pipe)) {
            if (fgets(buffer, 128, pipe) != nullptr) {
                output += buffer;
            }
        }
        
        // 获取命令退出状态
        int status = pclose(pipe);
        
        // 检查命令是否成功执行
        if (status != 0) {
            LOG_ERROR(LOG_TAG, "Unzip command failed with status %d", status);
            LOG_ERROR(LOG_TAG, "Command output: %s", output.c_str());
            return false;
        }
        LOG_INFO(LOG_TAG, "Successfully unzipped: %s -> %s", zipPath.c_str(), destPath.c_str());
        LOG_DEBUG(LOG_TAG, "Command output: %s", output.c_str());

    #else
        popen(command.c_str(), "r");
        LOG_INFO(LOG_TAG, "Successfully unzipped: %s -> %s", zipPath.c_str(), destPath.c_str());
    #endif
    
    return true;
}

} // namespace CloneMgrMw