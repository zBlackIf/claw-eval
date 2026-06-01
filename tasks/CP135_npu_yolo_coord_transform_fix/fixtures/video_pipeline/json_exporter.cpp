#include "json_exporter.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>

// Save detection results to JSON file
bool saveDetectionResultToJson(const std::string& json_path,
                               const std::string& image_path,
                               const DetectionResult& result,
                               int image_width,
                               int image_height) {
    if (image_width <= 0 || image_height <= 0) {
        return false;
    }

    std::ofstream ofs(json_path);
    if (!ofs.is_open()) {
        return false;
    }

    ofs << "{\n";
    ofs << "  \"image_path\": \"" << image_path << "\",\n";
    ofs << "  \"image_width\": " << image_width << ",\n";
    ofs << "  \"image_height\": " << image_height << ",\n";
    ofs << "  \"detected_count\": " << result.objects.size() << ",\n";
    ofs << "  \"detections\": [\n";

    const float VPSS_W         = 640.0f;
    const float VPSS_H         = 384.0f;
    const float BLACK_BORDER_H = 128.0f;

    for (size_t i = 0; i < result.objects.size(); ++i) {
        const auto& obj = result.objects[i];

        // Map from 640x640 (with borders) to original image pixel coordinates
        float orig_x = obj.rect.x * static_cast<float>(image_width) / VPSS_W;
        float orig_y = (obj.rect.y - BLACK_BORDER_H) * static_cast<float>(image_height) / VPSS_H;
        float orig_w = obj.rect.width * static_cast<float>(image_width) / VPSS_W;
        float orig_h = obj.rect.height * static_cast<float>(image_height) / VPSS_H;

        // Convert to YOLO normalized format (center_x, center_y, width, height)
        float center_x = (orig_x + orig_w / 2.0f) / static_cast<float>(image_width);
        float center_y = (orig_y + orig_h / 2.0f) / static_cast<float>(image_height);
        float norm_w   = orig_w / static_cast<float>(image_width);
        float norm_h   = orig_h / static_cast<float>(image_height);

        ofs << "    {\n";
        ofs << "      \"class_id\": " << obj.class_id << ",\n";
        ofs << "      \"class_name\": \"" << obj.class_name << "\",\n";
        ofs << "      \"confidence\": " << std::fixed << std::setprecision(4) << obj.confidence << ",\n";
        ofs << "      \"bbox\": {\n";
        ofs << "        \"center_x\": " << center_x << ",\n";
        ofs << "        \"center_y\": " << center_y << ",\n";
        ofs << "        \"width\": " << norm_w << ",\n";
        ofs << "        \"height\": " << norm_h << "\n";
        ofs << "      }\n";
        ofs << "    }";
        if (i < result.objects.size() - 1) ofs << ",";
        ofs << "\n";
    }

    ofs << "  ]\n";
    ofs << "}\n";
    ofs.close();
    return true;
}

// Save detection results to YOLO TXT file
// Each line: <class_id> <center_x> <center_y> <width> <height>
// All values normalized to 0.0~1.0 relative to original image
bool saveDetectionResultToTxt(const std::string& txt_path,
                               const DetectionResult& result,
                               int image_width,
                               int image_height) {
    if (image_width <= 0 || image_height <= 0) {
        return false;
    }

    std::ofstream ofs(txt_path);
    if (!ofs.is_open()) {
        return false;
    }

    const float VPSS_W         = 640.0f;
    const float VPSS_H         = 384.0f;
    const float BLACK_BORDER_H = 128.0f;

    for (const auto& obj : result.objects) {
        // Step 1: 640x640 (with borders) -> original image pixel coordinates
        float orig_x = obj.rect.x * static_cast<float>(image_width) / VPSS_W;
        float orig_y = (obj.rect.y - BLACK_BORDER_H) * static_cast<float>(image_height) / VPSS_H;
        float orig_w = obj.rect.width * static_cast<float>(image_width) / VPSS_W;
        float orig_h = obj.rect.height * static_cast<float>(image_height) / VPSS_H;

        // Step 2: Pixel coordinates -> YOLO normalized format
        float center_x = (orig_x + orig_w / 2.0f) / static_cast<float>(image_width);
        float center_y = (orig_y + orig_h / 2.0f) / static_cast<float>(image_height);
        float norm_w   = orig_w / static_cast<float>(image_width);
        float norm_h   = orig_h / static_cast<float>(image_height);

        // Clamp center to valid range for YOLO format
        center_x = std::max(0.0f, std::min(1.0f, center_x));
        center_y = std::max(0.0f, std::min(1.0f, center_y));

        ofs << obj.class_id << " "
            << std::fixed << std::setprecision(6)
            << center_x << " " << center_y << " "
            << norm_w << " " << norm_h << "\n";
    }

    ofs.close();
    return true;
}
