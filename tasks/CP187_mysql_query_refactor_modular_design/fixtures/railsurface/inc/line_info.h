#ifndef _RAILSURFACE_LINEINFO_H_
#define _RAILSURFACE_LINEINFO_H_

#include <string>
#include <vector>

struct detectionInfoStru {
    std::string line_name;
    int xing_bie;
    std::string project_path;
    int det_system;
    int acq_device;
};

struct defectInfo {
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

struct projectPath_interval {
    std::string project_path;
    double start_mileage;
    double end_mileage;
};

#endif
