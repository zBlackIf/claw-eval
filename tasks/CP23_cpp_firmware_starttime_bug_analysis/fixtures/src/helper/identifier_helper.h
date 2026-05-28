#ifndef IDENTIFIER_HELPER_H
#define IDENTIFIER_HELPER_H

#include <string>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>

namespace CloneMgrMw {

class IdentifierHelper {
public:
    static std::string getDateTimeString() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::tm tm_buf;
        localtime_r(&time, &tm_buf);
        std::ostringstream oss;
        oss << std::put_time(&tm_buf, "%Y-%m-%d %H:%M:%S");
        return oss.str();
    }

    static void writeStartTimeToDb(int itemType, const std::string& startTime) {
        // stub
    }

    static void writeEndTimeToDb(int itemType, const std::string& endTime) {
        // stub
    }

    static void writeLastStatusToDb(int itemType, const std::string& status) {
        // stub
    }
};

} // namespace CloneMgrMw

#endif // IDENTIFIER_HELPER_H
