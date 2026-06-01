#ifndef _RAILSURFACE_PROJECT_MANAGE_H_
#define _RAILSURFACE_PROJECT_MANAGE_H_

#include <string>
#include <vector>
#include "line_info.h"
#include "mysql_util.h"

class projectManage {
public:
    projectManage();
    ~projectManage();

    // Reads defect data from MySQL and stores in internal vector.
    // Currently calls myMYSQL::query_database() and manually parses the returned string.
    bool readMySQL(const detectionInfoStru& dinfo, double start_real_m, double end_real_m);

    // Exports defect data to CSV
    void writeCsv();

    std::vector<DefectInfo> getDefects() const { return m_defects; }

private:
    std::vector<DefectInfo> m_defects;
    myMYSQL* m_db;
};

#endif
