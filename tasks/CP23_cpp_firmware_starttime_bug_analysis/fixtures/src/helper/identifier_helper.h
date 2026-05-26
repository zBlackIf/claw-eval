#pragma once
#include <string>
#include <chrono>
#include <iomanip>
#include <sstream>

class IdentifierHelper {
public:
    static std::string getDateTimeString() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
        return ss.str();
    }

    static std::string generateUUID();
};
