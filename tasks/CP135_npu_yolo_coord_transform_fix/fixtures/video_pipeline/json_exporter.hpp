#pragma once

#include "video_detector.hpp"
#include <string>

// Save detection results to JSON file (YOLO normalized bbox format)
bool saveDetectionResultToJson(
    const std::string& json_path,
    const std::string& image_path,
    const DetectionResult& result,
    int image_width,
    int image_height);

// Save detection results to YOLO TXT file
// Format: <class_id> <center_x> <center_y> <width> <height>
// All values normalized to 0.0~1.0 relative to original image
bool saveDetectionResultToTxt(
    const std::string& txt_path,
    const DetectionResult& result,
    int image_width,
    int image_height);
