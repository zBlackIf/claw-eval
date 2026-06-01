#pragma once
#include <opencv2/opencv.hpp>
#include <string>
#include <vector>
#include <map>

// ============ Constants ============
#define YOLO_INPUT_WIDTH       640
#define YOLO_INPUT_HEIGHT      640
#define YOLO_SCALED_HEIGHT     384
#define YOLO_BORDER_HEIGHT     128
#define YOLO_MODEL_INPUT_SIZE  (640 * 640 * 3 / 2)  // NV12

#define VIS_FONT_SIZE_DEFAULT     0.6f
#define VIS_BOX_THICKNESS_DEFAULT 2

// ============ Data Structures ============
struct DetectedObject {
    int class_id;
    std::string class_name;
    float confidence;
    cv::Rect2f rect;  // In 640x640 coordinate space (with borders)
};

struct DetectionResult {
    std::vector<DetectedObject> objects;
    double timestamp;
    double start_time;
    double end_time;
};

// ============ ResultVisualizer ============
class ResultVisualizer {
public:
    ResultVisualizer();
    void drawDetections(cv::Mat& image, const DetectionResult& result,
                        bool draw_label = true, bool draw_confidence = true);
private:
    void drawObject(cv::Mat& image, const DetectedObject& obj,
                    const cv::Scalar& color, bool draw_label, bool draw_confidence);
    std::vector<cv::Scalar> generateColors(int count);
    float font_size_;
    int box_thickness_;
    int font_face_;
    std::map<int, cv::Scalar> class_colors_;
};

// ============ JSON/TXT Exporter ============
bool saveDetectionResultToJson(const std::string& json_path,
                               const std::string& image_path,
                               const DetectionResult& result,
                               int image_width, int image_height);

bool saveDetectionResultToTxt(const std::string& txt_path,
                              const DetectionResult& result,
                              int image_width, int image_height);

// ============ YoloDetector ============
class YoloDetector {
public:
    YoloDetector();
    ~YoloDetector();
    bool initialize(const std::string& model_path);
    DetectionResult detect(const cv::Mat& frame);
    DetectionResult detectImage(const cv::Mat& image);
private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

// ============ VideoPipeline ============
class VideoPipeline {
public:
    VideoPipeline();
    ~VideoPipeline();
    bool initialize(const std::string& model_path);
    DetectionResult detectImage(const cv::Mat& image);
    void processFrame(cv::Mat& frame);
private:
    std::unique_ptr<YoloDetector> detector_;
    std::unique_ptr<ResultVisualizer> visualizer_;
};
