#include "project_manage.h"
#include <sstream>
#include <fstream>

projectManage::projectManage() {
    m_db = new myMYSQL("main_db");
}

projectManage::~projectManage() {
    delete m_db;
}

// Reads MySQL data by calling query_database and manually parsing
// the comma-separated string output. This is brittle and should be refactored
// to use the structured return type from myMYSQL once query_database is updated.
bool projectManage::readMySQL(const detectionInfoStru& dinfo, double start_real_m, double end_real_m) {
    DetectionInterval interval;
    interval.line_name = dinfo.line_name;
    interval.xing_bie = dinfo.xing_bie;
    interval.project_path = dinfo.project_path;

    std::string raw = m_db->query_database(interval, start_real_m, end_real_m);
    if (raw.empty()) {
        return false;
    }

    // Parse the raw CSV string - one line per defect
    m_defects.clear();
    std::istringstream stream(raw);
    std::string line;
    while (std::getline(stream, line)) {
        if (line.empty()) continue;
        std::istringstream ls(line);
        std::string token;
        DefectInfo d;
        int col = 0;
        while (std::getline(ls, token, ',')) {
            switch (col) {
                case 0: d.line_name = token; break;
                case 1: d.xing_bie = std::stoi(token); break;
                case 2: d.mileage = std::stod(token); break;
                case 3: d.side = std::stoi(token); break;
                case 4: d.defect_position = std::stoi(token); break;
                case 5: d.defect_type = std::stoi(token); break;
                case 6: d.severity = std::stoi(token); break;
                case 7: d.x1 = std::stoi(token); break;
                case 8: d.rect_width = std::stoi(token); break;
                case 9: d.rect_height = std::stoi(token); break;
                case 10: d.image_path = token; break;
            }
            col++;
        }
        m_defects.push_back(d);
    }
    return true;
}

void projectManage::writeCsv() {
    std::ofstream ofs("defects_export.csv");
    ofs << "line_name,xing_bie,mileage,side,defect_position,defect_type,severity,x1,rect_width,rect_height,image_path" << std::endl;
    for (const auto& d : m_defects) {
        ofs << d.line_name << "," << d.xing_bie << "," << d.mileage << ","
            << d.side << "," << d.defect_position << "," << d.defect_type << ","
            << d.severity << "," << d.x1 << "," << d.rect_width << ","
            << d.rect_height << "," << d.image_path << std::endl;
    }
    ofs.close();
}
