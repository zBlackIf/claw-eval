#include "mysql_util.h"
#include <sstream>
#include <cstring>

extern MYSQL *conn;
extern MYSQL mysql_instance;
extern std::mutex g_dbLock;

std::string g_excel_filename;

myMYSQL::myMYSQL(std::string mysql_name) {
    my_mysql_name = mysql_name;
    ifConnected = false;
    mysql = nullptr;
    conn = nullptr;
    fd = nullptr;
    res = nullptr;
    port = 3306;
}

myMYSQL::~myMYSQL() {
    if (conn) {
        mysql_close(conn);
    }
}

bool myMYSQL::empty_database() {
    std::lock_guard<std::mutex> lock(_mysql_mutex);
    std::string sql = "DELETE FROM t_defect_records";
    if (mysql_query(conn, sql.c_str()) != 0) {
        std::cerr << "empty_database failed: " << mysql_error(conn) << std::endl;
        return false;
    }
    return true;
}

// This function is the main query function. It has grown organically and
// now has several issues:
// 1. Hardcoded column indices (magic numbers like row[1], row[6], row[9]...)
// 2. No null-safety when reading columns
// 3. Returns a concatenated string instead of structured data
// 4. SQL injection risk from string concatenation
// 5. Mixed concerns: query building, execution, and parsing all in one function
std::string myMYSQL::query_database(DetectionInterval interval, double start_mileage, double end_mileage) {
    std::lock_guard<std::mutex> lock(_mysql_mutex);
    std::string result = "";

    // Build query - concatenating user input directly (SQL injection risk)
    std::string sql_query = "SELECT * FROM t_defect_records WHERE line_name = '" +
        interval.line_name + "' AND xing_bie = " + std::to_string(interval.xing_bie) +
        " AND distance >= " + std::to_string(start_mileage) +
        " AND distance <= " + std::to_string(end_mileage) +
        " ORDER BY distance ASC";

    if (mysql_query(conn, sql_query.c_str()) != 0) {
        std::cerr << "Query failed: " << mysql_error(conn) << std::endl;
        return "";
    }

    res = mysql_store_result(conn);
    if (!res) {
        return "";
    }

    int num_fields = mysql_num_fields(res);
    int affected_rows = mysql_affected_rows(conn);

    // Log info
    std::cout << "Query: " << sql_query << std::endl;
    std::cout << "Affected rows: " << affected_rows << ", Fields: " << num_fields << std::endl;

    MYSQL_ROW row;
    while ((row = mysql_fetch_row(res))) {
        // Hardcoded column indices - fragile if table schema changes
        std::string line_name = row[1] ? row[1] : "";
        int xingbie = row[2] ? atoi(row[2]) : 0;
        double distance = row[6] ? atof(row[6]) : 0.0;
        int side = row[9] ? atoi(row[9]) : 0;
        int defect_pos = row[10] ? atoi(row[10]) : 0;
        int defect_type = row[11] ? atoi(row[11]) : 0;
        int severity = row[15] ? atoi(row[15]) : 0;
        int x1 = row[26] ? atoi(row[26]) : 0;
        int rect_width = row[28] ? atoi(row[28]) : 0;
        int rect_height = row[29] ? atoi(row[29]) : 0;
        std::string image_path = row[33] ? row[33] : "";

        // Concatenate into a single string (hard to parse by caller)
        result += line_name + "," + std::to_string(xingbie) + "," +
                  std::to_string(distance) + "," + std::to_string(side) + "," +
                  std::to_string(defect_pos) + "," + std::to_string(defect_type) + "," +
                  std::to_string(severity) + "," + std::to_string(x1) + "," +
                  std::to_string(rect_width) + "," + std::to_string(rect_height) + "," +
                  image_path + "\n";
    }

    mysql_free_result(res);
    return result;
}

int myMYSQL::init_mysql_DH_conn() {
    return 1;
}

int myMYSQL::init_imageflawdata_TABLE() {
    return 1;
}

int myMYSQL::init_imageflawinfo_TABLE() {
    return 1;
}

int myMYSQL::insert_data_to_DH(DefectInfo defect) {
    return 1;
}

int init_mysql_conn() {
    return 1;
}

int destroy_mysql_conn() {
    return 1;
}

std::string getYMDstring() {
    return "2026-01-14";
}

std::string getYMDHMSstring() {
    return "2026-01-14 10:00:00";
}
