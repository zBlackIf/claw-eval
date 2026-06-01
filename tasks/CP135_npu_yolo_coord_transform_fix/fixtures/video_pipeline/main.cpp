#include "video_detector.hpp"
#include <iostream>
#include <cstdint>
#include <vector>

// Simulates loading an image file, resizing to 640x384, then padding to 640x640 NV12
// Returns a full 640x640 NV12 buffer with proper black borders
std::vector<uint8_t> prepareImageForNPU(int orig_width, int orig_height) {
    // In real code: cv::imread -> cv::resize(640,384) -> cv::copyMakeBorder(128,128,0,0)
    // -> cv::cvtColor(BGR2YUV_I420) -> convert to NV12
    std::vector<uint8_t> nv12_buffer(YOLO_MODEL_INPUT_SIZE, 0);

    // Y-plane: top 128 rows = 0 (black), middle 384 rows = image data, bottom 128 rows = 0
    // Here we simulate with placeholder values
    for (int row = YOLO_BORDER_HEIGHT; row < YOLO_BORDER_HEIGHT + YOLO_SCALED_HEIGHT; ++row) {
        for (int col = 0; col < YOLO_INPUT_WIDTH; ++col) {
            nv12_buffer[row * YOLO_INPUT_WIDTH + col] = 128;  // gray pixel placeholder
        }
    }

    // UV-plane: set to 128 (neutral chroma)
    int uv_start = YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT;
    for (int i = uv_start; i < YOLO_MODEL_INPUT_SIZE; ++i) {
        nv12_buffer[i] = 128;
    }

    return nv12_buffer;
}

// Visualizer: maps detection coordinates from 640x640 (with borders) back to original image
// This is the CORRECT reference implementation for coordinate mapping
void drawDetections(int image_cols, int image_rows, const DetectionResult& result) {
    const float MODEL_INPUT_W = 640.0f;
    const float SCALED_H      = 384.0f;
    const float BORDER_H      = 128.0f;

    float scale_x = static_cast<float>(image_cols) / MODEL_INPUT_W;
    float scale_y = static_cast<float>(image_rows) / SCALED_H;

    for (const auto& obj : result.objects) {
        // Correct mapping: 640x640 coords -> original image coords
        float mapped_x = obj.rect.x * scale_x;
        float mapped_y = (obj.rect.y - BORDER_H) * scale_y;
        float mapped_w = obj.rect.width * scale_x;
        float mapped_h = obj.rect.height * scale_y;

        std::cout << "Draw box: (" << mapped_x << ", " << mapped_y
                  << ", " << mapped_w << ", " << mapped_h << ")\n";
    }
}

// main: demonstrates the pipeline for single image detection
// NOTE: The pipeline calls detectImage for JSON/TXT export and detect for visualization.
// These should produce IDENTICAL detection results for the same image, but currently don't.
int main() {
    const int ORIG_WIDTH = 3840;
    const int ORIG_HEIGHT = 2160;

    YoloDetectorAcl detector;

    // Prepare full 640x640 NV12 image with OpenCV (resize + pad)
    std::vector<uint8_t> nv12_full = prepareImageForNPU(ORIG_WIDTH, ORIG_HEIGHT);

    // Path 1: detectImage - used for JSON/TXT export
    // BUG: Only copies middle 384 rows, top/bottom borders contain garbage
    DetectionResult result_image = detector.detectImage(nv12_full.data(), ORIG_WIDTH, ORIG_HEIGHT);

    // Path 2: preprocess + detect - used for visualization
    // CORRECT: Buffer properly initialized, only updates middle 384 rows
    // But for single images we already have full 640x640, so this is wasteful
    // detector.preprocess(nv12_frame_384, 640, 384);
    // DetectionResult result_video = detector.detect();

    // The two paths should give the same results but don't because detectImage
    // leaves garbage data in the border regions of the NPU input buffer.

    // Draw using visualizer (correct coordinate mapping)
    drawDetections(ORIG_WIDTH, ORIG_HEIGHT, result_image);

    return 0;
}
