#include "video_detector.hpp"
#include <sstream>
#include <iomanip>

// ============ ResultVisualizer Implementation ============

ResultVisualizer::ResultVisualizer()
    : font_size_(VIS_FONT_SIZE_DEFAULT),
      box_thickness_(VIS_BOX_THICKNESS_DEFAULT),
      font_face_(cv::FONT_HERSHEY_SIMPLEX) {
    std::vector<cv::Scalar> colors = generateColors(14);
    for (int i = 0; i < (int)colors.size() && i < 14; ++i) {
        class_colors_[i] = colors[i];
    }
}

void ResultVisualizer::drawDetections(cv::Mat& image,
                                       const DetectionResult& result,
                                       bool draw_label,
                                       bool draw_confidence) {
    // Model input: 640x640 (effective content 640x384, top/bottom 128px black borders)
    const float MODEL_INPUT_W = 640.0f;
    const float SCALED_H      = 384.0f;
    const float BORDER_H      = 128.0f;

    float scale_x = static_cast<float>(image.cols) / MODEL_INPUT_W;
    float scale_y = static_cast<float>(image.rows) / SCALED_H;

    for (const auto& obj : result.objects) {
        auto it = class_colors_.find(obj.class_id);
        cv::Scalar color = (it != class_colors_.end()) ? it->second : cv::Scalar(0, 255, 0);

        // Map from 640x640 (with borders) coordinate system back to original image
        DetectedObject mapped_obj = obj;
        mapped_obj.rect.x      = obj.rect.x * scale_x;
        mapped_obj.rect.y      = (obj.rect.y - BORDER_H) * scale_y;
        mapped_obj.rect.width  = obj.rect.width * scale_x;
        mapped_obj.rect.height = obj.rect.height * scale_y;

        drawObject(image, mapped_obj, color, draw_label, draw_confidence);
    }
}

void ResultVisualizer::drawObject(cv::Mat& image,
                                   const DetectedObject& obj,
                                   const cv::Scalar& color,
                                   bool draw_label,
                                   bool draw_confidence) {
    cv::Rect box(
        static_cast<int>(obj.rect.x),
        static_cast<int>(obj.rect.y),
        static_cast<int>(obj.rect.width),
        static_cast<int>(obj.rect.height)
    );

    // Clamp to image bounds
    box &= cv::Rect(0, 0, image.cols, image.rows);
    if (box.width <= 0 || box.height <= 0) return;

    cv::rectangle(image, box, color, box_thickness_);

    if (draw_label) {
        std::string label = obj.class_name;
        if (draw_confidence) {
            std::ostringstream oss;
            oss << std::fixed << std::setprecision(2) << obj.confidence;
            label += " " + oss.str();
        }

        int baseline = 0;
        cv::Size text_size = cv::getTextSize(label, font_face_, font_size_, 1, &baseline);

        int label_y = std::max(box.y - 5, text_size.height + 2);
        cv::putText(image, label, cv::Point(box.x, label_y),
                    font_face_, font_size_, color, 1);
    }
}

std::vector<cv::Scalar> ResultVisualizer::generateColors(int count) {
    std::vector<cv::Scalar> colors;
    for (int i = 0; i < count; ++i) {
        int h = (i * 180 / count) % 180;
        cv::Mat hsv(1, 1, CV_8UC3, cv::Scalar(h, 255, 200));
        cv::Mat bgr;
        cv::cvtColor(hsv, bgr, cv::COLOR_HSV2BGR);
        auto* p = bgr.ptr<cv::Vec3b>(0);
        colors.emplace_back((*p)[0], (*p)[1], (*p)[2]);
    }
    return colors;
}
