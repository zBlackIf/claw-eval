#ifndef _RAILSURFACE_MYSQL_H_
#define _RAILSURFACE_MYSQL_H_

#include <mysql/mysql.h>
#include <iostream>
#include <string>
#include <vector>
#include <mutex>
#include <unordered_map>

struct DetectionInterval {
    std::string line_name;
    int xing_bie;
    std::string project_path;
};

struct DefectInfo {
    std::string line_name;
    int xing_bie;
    double mileage;
    int side;
    int defect_position;
    int defect_type;
    int severity;
    int x1;
    int rect_width;
    int rect_height;
    std::string image_path;
};

extern std::string g_excel_filename;

std::string getYMDstring();
std::string getYMDHMSstring();
int init_mysql_conn();
int destroy_mysql_conn();

class myMYSQL {
    public:
        myMYSQL(std::string mysql_name);
        ~myMYSQL();

        bool empty_database();

        // TODO: query_database returns a raw string of concatenated results,
        // callers must manually parse the output.
        // The function is ~120 lines long with hardcoded column indices.
        std::string query_database(DetectionInterval interval, double start_mileage, double end_mileage);

        int init_mysql_DH_conn();
        int init_imageflawdata_TABLE();
        int init_imageflawinfo_TABLE();
        int insert_data_to_DH(DefectInfo defect);

    private:
        MYSQL* mysql;
        MYSQL* conn;
        MYSQL_FIELD *fd;
        MYSQL_RES *res;
        MYSQL_ROW column;
        std::string host;
        std::string user;
        std::string psw;
        std::string db;
        std::string my_mysql_name;
        std::mutex _mysql_mutex;
        int port;

    public:
        bool ifConnected;
};

#endif
