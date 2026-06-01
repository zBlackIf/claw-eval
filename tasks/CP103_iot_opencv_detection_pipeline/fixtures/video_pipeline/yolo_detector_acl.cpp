#include "video_detector.hpp"
#include <cstring>
#include <iostream>

// ============ YoloDetector::Impl ============
class YoloDetector::Impl {
public:
    Impl() : confidence_threshold_(0.5f), nms_threshold_(0.5f),
             is_initialized_(false), input_buffer_(nullptr) {}

    ~Impl() {
        if (input_buffer_) {
            delete[] input_buffer_;
            input_buffer_ = nullptr;
        }
    }

    bool initialize(const std::string& model_path) {
        // Simulate model loading (in real code this would load ACL model)
        model_path_ = model_path;
        input_buffer_ = new uint8_t[YOLO_MODEL_INPUT_SIZE]();
        is_initialized_ = true;
        return true;
    }

    // detect() - used for video stream frames (VPSS path)
    // Correct: does full 640x640 buffer copy including black borders
    DetectionResult detect(const cv::Mat& frame) {
        DetectionResult result;
        result.timestamp = cv::getTickCount() / cv::getTickFrequency();
        result.start_time = result.timestamp;

        if (!is_initialized_ || frame.empty()) {
            return result;
        }

        // Preprocess: resize to 640x384, pad to 640x640
        cv::Mat scaled_mat;
        cv::resize(frame, scaled_mat, cv::Size(YOLO_INPUT_WIDTH, YOLO_SCALED_HEIGHT));

        cv::Mat padded_mat(YOLO_INPUT_HEIGHT, YOLO_INPUT_WIDTH, CV_8UC3, cv::Scalar(0, 0, 0));
        cv::Rect roi(0, YOLO_BORDER_HEIGHT, YOLO_INPUT_WIDTH, YOLO_SCALED_HEIGHT);
        scaled_mat.copyTo(padded_mat(roi));

        // Convert to NV12 and copy FULL buffer (correct approach)
        cv::Mat yuv_mat;
        cv::cvtColor(padded_mat, yuv_mat, cv::COLOR_BGR2YUV_I420);

        // Full buffer copy - black borders are properly zeroed
        std::memcpy(input_buffer_, yuv_mat.data, YOLO_MODEL_INPUT_SIZE);

        // Simulate NPU inference (return mock detections for testing)
        result = simulateInference();
        result.end_time = cv::getTickCount() / cv::getTickFrequency();
        return result;
    }

    // detectImage() - used for single image processing (JSON/TXT export)
    DetectionResult detectImage(const cv::Mat& image) {
        DetectionResult result;
        result.timestamp = cv::getTickCount() / cv::getTickFrequency();
        result.start_time = result.timestamp;

        if (!is_initialized_ || image.empty()) {
            return result;
        }

        // Resize to 640x384 (non-aspect-preserving stretch)
        cv::Mat scaled_mat;
        cv::resize(image, scaled_mat, cv::Size(YOLO_INPUT_WIDTH, YOLO_SCALED_HEIGHT));

        // Convert to NV12
        cv::Mat nv12_mat;
        cv::cvtColor(scaled_mat, nv12_mat, cv::COLOR_BGR2YUV_I420);

        // Copy effective 384 rows to offset position in buffer
        // Mimics VPSS behavior where hardware only outputs 384 rows
        int y_plane_offset = YOLO_BORDER_HEIGHT * YOLO_INPUT_WIDTH;
        int y_plane_size = YOLO_INPUT_WIDTH * YOLO_SCALED_HEIGHT;
        std::memcpy(input_buffer_ + y_plane_offset, nv12_mat.data, y_plane_size);

        // UV plane - partial copy
        int uv_base = YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT;
        int uv_offset = (YOLO_BORDER_HEIGHT / 2) * YOLO_INPUT_WIDTH;
        int uv_size = (YOLO_SCALED_HEIGHT / 2) * YOLO_INPUT_WIDTH;
        std::memcpy(input_buffer_ + uv_base + uv_offset,
                    nv12_mat.data + y_plane_size, uv_size);

        // Simulate NPU inference
        result = simulateInference();
        result.end_time = cv::getTickCount() / cv::getTickFrequency();
        return result;
    }

private:
    DetectionResult simulateInference() {
        // Returns mock detection results in 640x640 coordinate space
        DetectionResult result;
        result.timestamp = cv::getTickCount() / cv::getTickFrequency();
        result.start_time = result.timestamp;

        // Simulated detections (in 640x640 coord space with borders)
        DetectedObject obj1;
        obj1.class_id = 0;
        obj1.class_name = "person";
        obj1.confidence = 0.92f;
        obj1.rect = cv::Rect2f(200.0f, 256.0f, 80.0f, 150.0f);  // center of image
        result.objects.push_back(obj1);

        DetectedObject obj2;
        obj2.class_id = 2;
        obj2.class_name = "car";
        obj2.confidence = 0.87f;
        obj2.rect = cv::Rect2f(400.0f, 300.0f, 120.0f, 90.0f);
        result.objects.push_back(obj2);

        result.end_time = cv::getTickCount() / cv::getTickFrequency();
        return result;
    }

    float confidence_threshold_;
    float nms_threshold_;
    bool is_initialized_;
    uint8_t* input_buffer_;
    std::string model_path_;
};

// ============ YoloDetector ============
YoloDetector::YoloDetector() : impl_(std::make_unique<Impl>()) {}
YoloDetector::~YoloDetector() = default;

bool YoloDetector::initialize(const std::string& model_path) {
    return impl_->initialize(model_path);
}

DetectionResult YoloDetector::detect(const cv::Mat& frame) {
    return impl_->detect(frame);
}

DetectionResult YoloDetector::detectImage(const cv::Mat& image) {
    return impl_->detectImage(image);
}

// ============ VideoPipeline ============
VideoPipeline::VideoPipeline()
    : detector_(std::make_unique<YoloDetector>()),
      visualizer_(std::make_unique<ResultVisualizer>()) {}
VideoPipeline::~VideoPipeline() = default;

bool VideoPipeline::initialize(const std::string& model_path) {
    return detector_->initialize(model_path);
}

DetectionResult VideoPipeline::detectImage(const cv::Mat& image) {
    return detector_->detectImage(image);
}

void VideoPipeline::processFrame(cv::Mat& frame) {
    DetectionResult result = detector_->detect(frame);
    visualizer_->drawDetections(frame, result);
}
