# Video Pipeline - YOLO Detection System

NPU-based object detection pipeline for embedded Linux (RV1126/3588).

## Architecture

- **YoloDetector**: Handles model inference via ACL (Ascend Computing Language)
  - `detect()`: Video stream path (VPSS hardware provides 640x384 NV12)
  - `detectImage()`: Single image path (OpenCV resize + padding)
- **ResultVisualizer**: Draws bounding boxes on frames for display
- **JSON/TXT Exporter**: Saves detection results in YOLO normalized format

## Coordinate System

NPU input: 640x640 (640x384 effective content + 128px top/bottom black border padding)

The pipeline handles coordinate mapping from NPU output space (640x640) back to
original image coordinates for visualization and export.

## Build

```bash
mkdir build && cd build
cmake .. && make
```

## Usage

```bash
./video_pipeline <image_path> <output_dir>
```

## Known Issues

- Visualizer draws boxes correctly for video stream path
- JSON/TXT export coordinates are not matching visualizer output for the same detections
- Reported by QA: exported annotations have incorrect Y-coordinates and heights
  when validated against ground truth labels
