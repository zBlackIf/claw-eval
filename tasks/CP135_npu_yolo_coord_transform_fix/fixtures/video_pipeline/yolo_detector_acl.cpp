#include "video_detector.hpp"
#include <cstring>

// Initialize the input buffer with proper black borders (NV12 format)
// Y-plane: all zeros for black; UV-plane: 128 for neutral chroma
void YoloDetectorAcl::initBuffer() {
    // Zero out Y-plane (640*640 bytes)
    std::memset(input_buffer_, 0, YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT);
    // Set UV-plane to 128 (neutral chroma for NV12)
    std::memset(input_buffer_ + YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT,
                128,
                YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT / 2);
    initialized_ = true;
}

// preprocess: For video frames from VPSS (640x384 NV12 data)
// The buffer is already initialized with black borders, so we only
// update the middle 384 rows of the Y-plane and corresponding UV rows.
bool YoloDetectorAcl::preprocess(const uint8_t* nv12_frame_384, int frame_width, int frame_height) {
    if (!initialized_) {
        initBuffer();
    }
    if (frame_width != YOLO_INPUT_WIDTH || frame_height != YOLO_SCALED_HEIGHT) {
        return false;
    }

    // Copy Y-plane: 384 rows into the middle of the 640-row buffer
    std::memcpy(
        input_buffer_ + YOLO_BORDER_HEIGHT * YOLO_INPUT_WIDTH,   // dest: skip top 128 rows
        nv12_frame_384,                                           // src: full Y of 640x384
        YOLO_INPUT_WIDTH * YOLO_SCALED_HEIGHT                    // size: 640*384 bytes
    );

    // Copy UV-plane: 192 rows into the middle of the 320-row UV section
    const int uv_offset_src = YOLO_INPUT_WIDTH * YOLO_SCALED_HEIGHT;
    const int uv_offset_dst = YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT  // after full Y-plane
                            + (YOLO_BORDER_HEIGHT / 2) * YOLO_INPUT_WIDTH;  // skip top border UV
    std::memcpy(
        input_buffer_ + uv_offset_dst,
        nv12_frame_384 + uv_offset_src,
        YOLO_INPUT_WIDTH * (YOLO_SCALED_HEIGHT / 2)
    );

    return true;
}

// detectImage: For single images processed by OpenCV
// OpenCV produces a full 640x640 NV12 buffer (with padding already applied).
// Mimics VPSS-style partial copy to keep the interface consistent with video path.
DetectionResult YoloDetectorAcl::detectImage(const uint8_t* nv12_640x640, int orig_width, int orig_height) {
    // Copy image data to NPU input buffer (matching VPSS behavior: only effective region)
    std::memcpy(
        input_buffer_ + YOLO_BORDER_HEIGHT * YOLO_INPUT_WIDTH,  // dest: offset to effective region
        nv12_640x640,                                            // src: NV12 data from OpenCV
        YOLO_INPUT_WIDTH * YOLO_SCALED_HEIGHT                   // size: 384 rows of Y-plane
    );

    // UV-plane copy
    const int y_plane_size = YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT;
    std::memcpy(
        input_buffer_ + y_plane_size + (YOLO_BORDER_HEIGHT / 2) * YOLO_INPUT_WIDTH,
        nv12_640x640 + YOLO_INPUT_WIDTH * YOLO_INPUT_HEIGHT,    // UV data from source
        YOLO_INPUT_WIDTH * (YOLO_SCALED_HEIGHT / 2)
    );

    // Simulate NPU inference (in real code this calls ACL APIs)
    return DetectionResult{parseOutput(orig_width, orig_height)};
}

// detect: Run inference on the prepared buffer (used after preprocess)
DetectionResult YoloDetectorAcl::detect() {
    // Simulate inference - in reality calls aclmdlExecute
    return DetectionResult{parseOutput(0, 0)};
}

// Simulate NPU output parsing (placeholder)
std::vector<DetectedObject> YoloDetectorAcl::parseOutput(int orig_width, int orig_height) {
    // In real code: parse NPU output tensor, apply NMS, return detected objects
    // Objects have rect in 640x640 coordinate system (including black borders)
    return {};
}
