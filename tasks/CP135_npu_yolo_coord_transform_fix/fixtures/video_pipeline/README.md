# NPU YOLO Detection Pipeline

## Overview

This module implements YOLO object detection on an NPU (Neural Processing Unit) for an embedded video surveillance system. The pipeline handles:

1. **Video frames** (from VPSS hardware): 640x384 NV12 → preprocess → detect → visualize
2. **Single images** (from file): OpenCV resize+pad to 640x640 NV12 → detectImage → export to JSON/TXT

## Architecture

```
Original Image (e.g., 3840x2160)
    │
    ├─[Video Path]──→ VPSS outputs 640×384 NV12
    │                    │
    │                    └─→ preprocess() ──→ detect() ──→ drawDetections()
    │                         (updates middle 384 rows;      (correct coords)
    │                          border pre-initialized)
    │
    └─[Image Path]──→ OpenCV resize(640,384) + pad(128,128,0,0) = 640×640 NV12
                         │
                         └─→ detectImage() ──→ saveDetectionResultToJson/Txt()
                              (copies to NPU buffer)   (coordinate mapping)
```

## Coordinate System

- **NPU output**: Bounding boxes in 640×640 coordinate system (includes 128px top/bottom black borders)
- **Effective region**: 640×384 (rows 128-511 of the 640×640 frame)
- **Mapping to original image**:
  - x: `npu_x * (orig_width / 640)`
  - y: `(npu_y - 128) * (orig_height / 384)`

## Known Issues

Users report that JSON/TXT export coordinates are inconsistent with the visualizer overlay:
- Visualizer draws boxes correctly on the original image
- JSON/TXT export produces coordinates that appear "too small" or "offset downward"
- The issue only manifests with the single-image (detectImage) path, not with video frames

## Build

```bash
# Cross-compile for embedded target (Ascend 310 / Hi3559 etc.)
# Requires: ACL runtime, OpenCV 4.x, cJSON
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=../toolchain.cmake
make -j4
```

## File Structure

- `video_detector.hpp` — Detector class declaration and constants
- `yolo_detector_acl.cpp` — NPU inference implementation (preprocess, detect, detectImage)
- `json_exporter.hpp/.cpp` — Detection result export (JSON + YOLO TXT format)
- `main.cpp` — Entry point demonstrating both paths
