#pragma once

#include <string>
#include <vector>
#include <cstdint>

// Simulated cv namespace for compilation without OpenCV
namespace cv {
    struct Rect2f {
        float x = 0, y = 0, width = 0, height = 0;
    };
    struct Size {
        int width = 0, height = 0;
        Size() = default;
        Size(int w, int h) : width(w), height(h) {}
    };
}

struct DetectedObject {
    int class_id = 0;
    std::string class_name;
    float confidence = 0.0f;
    cv::Rect2f rect;  // in 640x640 coordinate system (with letterbox borders)
};

struct DetectionResult {
    std::vector<DetectedObject> objects;
    double timestamp = 0.0;
    double start_time = 0.0;
    double end_time = 0.0;
};

// Constants for YOLO model input
constexpr int YOLO_INPUT_WIDTH     = 640;
constexpr int YOLO_INPUT_HEIGHT    = 640;
constexpr int YOLO_SCALED_HEIGHT   = 384;   // effective image height after letterbox
constexpr int YOLO_BORDER_HEIGHT   = 128;   // top/bottom black border = (640-384)/2
constexpr int YOLO_MODEL_INPUT_SIZE = YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT * 3 / 2;  // NV12

class YoloDetectorAcl {
public:
    YoloDetectorAcl() = default;

    // For video frames: VPSS provides 640x384 NV12, we only update middle rows
    // Buffer is pre-initialized with black borders at construction time
    bool preprocess(const uint8_t* nv12_frame_384, int frame_width, int frame_height);
    DetectionResult detect();

    // For single image: OpenCV does resize+pad to full 640x640 NV12
    DetectionResult detectImage(const uint8_t* nv12_640x640, int orig_width, int orig_height);

private:
    uint8_t input_buffer_[YOLO_MODEL_INPUT_SIZE] = {0};
    bool initialized_ = false;

    void initBuffer();
    std::vector<DetectedObject> parseOutput(int orig_width, int orig_height);
};
