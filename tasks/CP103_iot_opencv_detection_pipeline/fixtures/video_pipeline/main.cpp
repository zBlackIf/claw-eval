#include "video_detector.hpp"
#include <iostream>
#include <filesystem>

namespace fs = std::filesystem;

void printUsage(const char* prog) {
    std::cerr << "Usage: " << prog << " <image_path> <output_dir>" << std::endl;
    std::cerr << "  Runs YOLO detection on image, saves visualization + JSON + TXT" << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printUsage(argv[0]);
        return 1;
    }

    std::string image_path = argv[1];
    std::string output_dir = argv[2];
    std::string model_path = "model/yolov8n.om";  // ACL model file

    // Load image
    cv::Mat image = cv::imread(image_path);
    if (image.empty()) {
        std::cerr << "Error: Cannot load image: " << image_path << std::endl;
        return 1;
    }

    std::cout << "Image loaded: " << image.cols << "x" << image.rows << std::endl;

    // Create output directory
    fs::create_directories(output_dir);

    // Initialize pipeline
    VideoPipeline pipeline;
    if (!pipeline.initialize(model_path)) {
        std::cerr << "Error: Failed to initialize pipeline" << std::endl;
        return 1;
    }

    // --- Path 1: Single image detection for JSON/TXT export ---
    DetectionResult result = pipeline.detectImage(image);
    std::cout << "Detected " << result.objects.size() << " objects" << std::endl;

    // Save JSON (YOLO normalized format)
    std::string json_path = output_dir + "/detections.json";
    if (saveDetectionResultToJson(json_path, image_path, result,
                                   image.cols, image.rows)) {
        std::cout << "JSON saved: " << json_path << std::endl;
    }

    // Save TXT (YOLO format: class_id cx cy w h)
    std::string txt_path = output_dir + "/detections.txt";
    if (saveDetectionResultToTxt(txt_path, result, image.cols, image.rows)) {
        std::cout << "TXT saved: " << txt_path << std::endl;
    }

    // --- Path 2: Video-style detection for visualization ---
    cv::Mat vis_image = image.clone();
    pipeline.processFrame(vis_image);

    std::string vis_path = output_dir + "/visualization.jpg";
    cv::imwrite(vis_path, vis_image);
    std::cout << "Visualization saved: " << vis_path << std::endl;

    return 0;
}
