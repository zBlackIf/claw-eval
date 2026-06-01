#include "video_detector.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <cmath>

// Minimal cJSON-like implementation for self-contained build
namespace {
struct JsonBuilder {
    std::ostringstream ss;
    bool first = true;
    void beginObject() { ss << "{"; first = true; }
    void endObject()   { ss << "}"; }
    void beginArray()  { ss << "["; first = true; }
    void endArray()    { ss << "]"; }
    void sep() { if (!first) ss << ","; first = false; }
    void key(const std::string& k) { sep(); ss << "\"" << k << "\":"; first = true; }
    void valStr(const std::string& v) { sep(); ss << "\"" << v << "\""; }
    void valNum(double v) { sep(); ss << std::fixed << std::setprecision(6) << v; }
    void valInt(int v) { sep(); ss << v; }
    std::string str() const { return ss.str(); }
};
}  // namespace

// Save detection results to JSON file (YOLO normalized format)
bool saveDetectionResultToJson(const std::string& json_path,
                               const std::string& image_path,
                               const DetectionResult& result,
                               int image_width, int image_height) {
    JsonBuilder root;
    root.beginObject();
    root.key("image_path"); root.valStr(image_path);
    std::string name = image_path.substr(image_path.find_last_of('/') + 1);
    root.key("image_name"); root.valStr(name);
    root.key("image_width"); root.valInt(image_width);
    root.key("image_height"); root.valInt(image_height);
    root.key("timestamp"); root.valNum(result.timestamp);
    root.key("inference_time_ms"); root.valNum((result.end_time - result.start_time) * 1000.0);
    root.key("detected_count"); root.valInt((int)result.objects.size());

    root.key("detections");
    root.beginArray();

    for (const auto& obj : result.objects) {
        root.sep();
        root.beginObject();
        root.key("class_id"); root.valInt(obj.class_id);
        root.key("class_name"); root.valStr(obj.class_name);
        root.key("confidence"); root.valNum(obj.confidence);

        const float MODEL_INPUT_W  = 640.0f;
        const float BLACK_BORDER_H = 128.0f;

        float orig_x = obj.rect.x * static_cast<float>(image_width) / MODEL_INPUT_W;
        float orig_y = (obj.rect.y - BLACK_BORDER_H) * static_cast<float>(image_height) / MODEL_INPUT_W;
        float orig_w = obj.rect.width * static_cast<float>(image_width) / MODEL_INPUT_W;
        float orig_h = obj.rect.height * static_cast<float>(image_height) / MODEL_INPUT_W;

        // Normalize to 0-1 (YOLO format: center_x, center_y, width, height)
        float center_x = (orig_x + orig_w / 2.0f) / static_cast<float>(image_width);
        float center_y = (orig_y + orig_h / 2.0f) / static_cast<float>(image_height);
        float norm_w   = orig_w / static_cast<float>(image_width);
        float norm_h   = orig_h / static_cast<float>(image_height);

        // Clamp to [0, 1]
        center_x = std::max(0.0f, std::min(1.0f, center_x));
        center_y = std::max(0.0f, std::min(1.0f, center_y));
        norm_w   = std::max(0.0f, std::min(1.0f, norm_w));
        norm_h   = std::max(0.0f, std::min(1.0f, norm_h));

        root.key("bbox");
        root.beginObject();
        root.key("center_x"); root.valNum(center_x);
        root.key("center_y"); root.valNum(center_y);
        root.key("width");    root.valNum(norm_w);
        root.key("height");   root.valNum(norm_h);
        root.endObject();

        root.endObject();
    }

    root.endArray();
    root.endObject();

    std::ofstream ofs(json_path);
    if (!ofs.is_open()) return false;
    ofs << root.str();
    return ofs.good();
}

// Save detection results to TXT file (YOLO format: class_id cx cy w h)
bool saveDetectionResultToTxt(const std::string& txt_path,
                              const DetectionResult& result,
                              int image_width, int image_height) {
    std::ofstream ofs(txt_path);
    if (!ofs.is_open()) return false;

    for (const auto& obj : result.objects) {
        const float MODEL_INPUT_W  = 640.0f;
        const float BLACK_BORDER_H = 128.0f;

        float orig_x = obj.rect.x * static_cast<float>(image_width) / MODEL_INPUT_W;
        float orig_y = (obj.rect.y - BLACK_BORDER_H) * static_cast<float>(image_height) / MODEL_INPUT_W;
        float orig_w = obj.rect.width * static_cast<float>(image_width) / MODEL_INPUT_W;
        float orig_h = obj.rect.height * static_cast<float>(image_height) / MODEL_INPUT_W;

        float center_x = (orig_x + orig_w / 2.0f) / static_cast<float>(image_width);
        float center_y = (orig_y + orig_h / 2.0f) / static_cast<float>(image_height);
        float norm_w   = orig_w / static_cast<float>(image_width);
        float norm_h   = orig_h / static_cast<float>(image_height);

        // Clamp
        center_x = std::max(0.0f, std::min(1.0f, center_x));
        center_y = std::max(0.0f, std::min(1.0f, center_y));
        norm_w   = std::max(0.0f, std::min(1.0f, norm_w));
        norm_h   = std::max(0.0f, std::min(1.0f, norm_h));

        ofs << obj.class_id << " "
            << std::fixed << std::setprecision(6)
            << center_x << " " << center_y << " "
            << norm_w << " " << norm_h << "\n";
    }

    return ofs.good();
}
