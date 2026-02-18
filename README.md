# NASA SpaceCage Video Undistortion Tool

A self-contained, portable tool for correcting the spherical aberration of the filter cameras of the AEM-X mouse vivariums used by NASA aboard the International Space Station. This workflow uses the internal metal wire grid as a calibration reference.

## Overview

This tool corrects for spherical aberration in Filter Camera videos by:
1. Using labeled grid segments (ROIs) as calibration references
2. Estimating camera intrinsic parameters and distortion coefficients
3. Applying undistortion to produce corrected video output

## Quick Start

### Installation

```bash
# Install from the project directory
pip install -e .
```

### Basic Usage

```bash
# Undistort a video (ROI file is auto-detected as <video>.rois.yml)
spacecage-undistort video.mp4 -o undistorted.mp4

# Save calibration for reuse on other videos from the same camera
spacecage-undistort video.mp4 -o undistorted.mp4 --save-calibration calibration.yml

# Use existing calibration (faster, skips calibration step)
spacecage-undistort video2.mp4 -o undistorted2.mp4 --calibration calibration.yml

# Transform SLEAP tracking coordinates to match undistorted videos
spacecage-transform-coords labels.slp -o labels_undistorted.slp --calibration calibration.yml
```

## ROI Labeling

Before running the undistortion tool, you need to label the calibration grid segments in your video. Use [labelroi](https://github.com/talmolab/labelroi) from Talmo's lab:

```bash
# Install labelroi
pip install labelroi

# Label grid segments in your video
labelroi your_video.mp4
```

This will create a `your_video.rois.yml` file with the labeled segments.

### What to Label

Label the grid segments visible in your video as polygons. Each segment should be:
- Named as "segment1", "segment2", etc.
- A 4-point polygon outlining the grid square
- Labeled consistently across the same physical grid layout

The tool supports up to 34 segments in the default NASA SpaceCage layout (see below).

## Camera Intrinsic Parameters

### When Can You Reuse Calibration?

You can reuse camera calibration parameters (`--calibration` flag) when:
- The camera position and angle **remain the same** between recordings
- The camera's optical properties haven't changed (same lens, focus, zoom)
- The videos are from the **same camera setup**

### When You MUST Relabel ROIs

You need to create new ROI labels when:
- The camera **moves to a different position**
- The camera **angle or orientation changes**
- You're using a **different camera**
- The **focus or zoom settings** change

**Important:** Even if you're using saved calibration parameters, each video with a different camera position/angle needs its own ROI labeling to establish the correspondence between the grid and the image.

## Coordinate Transformation for Tracking Labels

If you have SLEAP tracking labels (`.slp` files) for your original videos, you can transform the coordinates to match the undistorted videos.

### CLI Usage

```bash
# Transform a single SLEAP file
spacecage-transform-coords labels.slp \
    -o labels_undistorted.slp \
    --calibration calibration.yml

# Batch transform multiple files
spacecage-transform-coords labels1.slp labels2.slp labels3.slp \
    -o output_directory/ \
    --calibration calibration.yml

# Custom video filename suffix (default: _undistorted)
spacecage-transform-coords labels.slp \
    -o labels_undistorted.slp \
    --calibration calibration.yml \
    --video-suffix _my_custom_suffix
```

### Python API

```python
from spacecage_undistort import transform_slp_coordinates

# Transform SLEAP file
transform_slp_coordinates(
    slp_input_path="labels.slp",
    slp_output_path="labels_undistorted.slp",
    calibration_path="calibration.yml",
    undistorted_video_suffix="_undistorted"
)
```

The coordinate transformation:
- Applies the same undistortion to tracking coordinates as was applied to video frames
- Updates video file paths in the SLEAP file to point to undistorted videos
- Preserves NaN values (missing tracking data)
- Works with multi-animal tracking and all SLEAP skeleton formats

**Note:** This performs undistortion only (not rectification). Coordinates remain in pixel space.

## Command-Line Reference

### Video Undistortion

```
usage: spacecage-undistort [-h] [-o OUTPUT] [--rois ROIS] [--calibration CALIBRATION]
                           [--save-calibration SAVE_CALIBRATION] [--calibrate-only]
                           [--side-length SIDE_LENGTH] video

Arguments:
  video                 Input video file path

Options:
  -o, --output OUTPUT   Output undistorted video path
  --rois ROIS          ROI YAML file path (default: auto-detect)
  --calibration CALIB  Load existing calibration file
  --save-calibration   Save calibration for reuse
  --calibrate-only     Only calibrate, don't undistort
  --side-length FLOAT  Grid square size in meters (default: 0.01 = 1cm)
```

### Coordinate Transformation

```
usage: spacecage-transform-coords [-h] -o OUTPUT --calibration CALIBRATION
                                  [--video-suffix VIDEO_SUFFIX]
                                  slp_files [slp_files ...]

Arguments:
  slp_files            Input SLEAP .slp file(s)

Options:
  -o, --output OUTPUT  Output path (file for single input, directory for batch)
  --calibration CALIB  Path to calibration YAML file
  --video-suffix STR   Suffix to add to video filenames (default: _undistorted)
```

## Python API

You can also use the tool programmatically:

```python
from spacecage_undistort import UndistortionPipeline

# Initialize pipeline
pipeline = UndistortionPipeline(
    video_path="video.mp4",
    roi_path="video.rois.yml"  # Optional, auto-detected if not provided
)

# Calibrate camera
calibration = pipeline.calibrate(
    save_calibration_path="calibration.yml",  # Optional
    side_length_m=0.01  # 1cm grid squares
)

# Undistort video
pipeline.undistort_video("undistorted.mp4")

# Or undistort a single frame
import cv2
frame = cv2.imread("frame.jpg")
undistorted_frame = pipeline.undistort_frame(frame)
```

## Default Grid Layout

The tool uses a 34-segment grid layout for NASA SpaceCage:

```
Segment layout (34 segments total):
- Each segment is a 1cm × 1cm square
- Layout is defined relative to segment1 at origin (0,0)
- Grid extends in a specific pattern to cover the cage
```

You can customize the grid layout by providing a custom segment offset dictionary in the Python API.

## Calibration Process

The tool performs the following steps:

1. **Load ROIs**: Reads labeled grid segments from YAML file
2. **Create Model Grid**: Generates ideal 3D grid geometry (1cm squares)
3. **Correspondence Matching**: Matches model grid to video ROIs
4. **Camera Calibration**: Estimates intrinsic matrix K and distortion coefficients using OpenCV
5. **Create Undistortion Maps**: Precomputes efficient remapping
6. **Apply Undistortion**: Processes video frame-by-frame

### Calibration Quality

After calibration, check the RMS reprojection error:
- **< 5 pixels**: Excellent calibration
- **5-10 pixels**: Good calibration
- **> 10 pixels**: May indicate labeling errors or poor grid visibility

## Files and Formats

### Input Files
- **Video**: MP4 or other formats supported by OpenCV
- **ROI File**: YAML format from labelroi (`.rois.yml`)

### Output Files
- **Undistorted Video**: MP4 format
- **Calibration File**: YAML format with camera parameters

### Calibration File Format

```yaml
camera_matrix:
  - [fx, 0, cx]
  - [0, fy, cy]
  - [0, 0, 1]
distortion_coefficients: [k1, k2, p1, p2, k3]
image_width: 640
image_height: 480
rms_error: 3.5
```

## Troubleshooting

### "ROI file not found"
- Make sure you've labeled the video with labelroi first
- Or specify the ROI file path with `--rois`

### "Need at least 3 overlapping segments"
- Label more grid segments in your video (at least 3 required)
- Make sure segment names match the expected format ("segment1", "segment2", etc.)

### High RMS error (> 10 pixels)
- Check that ROI labels accurately outline the grid squares
- Ensure the grid is clearly visible in the video
- Try labeling more segments for better calibration

### "Camera changes angle or position"
- You must create new ROI labels for each camera position/angle
- You can reuse the calibration parameters only if the camera hasn't moved

## Example Workflow

### First Video with Tracking Labels (New Camera Setup)
```bash
# 1. Label the grid segments
labelroi experiment1_video1.mp4

# 2. Calibrate and undistort, save calibration
spacecage-undistort experiment1_video1.mp4 \
    -o undistorted1.mp4 \
    --save-calibration exp1_calibration.yml

# 3. Transform SLEAP tracking coordinates (if you have them)
spacecage-transform-coords labels1.slp \
    -o labels1_undistorted.slp \
    --calibration exp1_calibration.yml
```

### Second Video (Same Camera Position)
```bash
# Camera hasn't moved - use saved calibration
spacecage-undistort experiment1_video2.mp4 \
    -o undistorted2.mp4 \
    --calibration exp1_calibration.yml

# Transform coordinates for second video
spacecage-transform-coords labels2.slp \
    -o labels2_undistorted.slp \
    --calibration exp1_calibration.yml
```

### Third Video (Camera Moved)
```bash
# Camera position changed - need new ROI labels
labelroi experiment2_video1.mp4

# Calibrate with new ROIs, save new calibration
spacecage-undistort experiment2_video1.mp4 \
    -o undistorted3.mp4 \
    --save-calibration exp2_calibration.yml

# Transform coordinates with new calibration
spacecage-transform-coords labels3.slp \
    -o labels3_undistorted.slp \
    --calibration exp2_calibration.yml
```

## SpaceCage Dimensions

Based on grid counting:
- **Bottom**: 15.5 units (y-axis) × 25 units (x-axis)
- **Height**: 25 units (z-axis)
- **Side**: 25 units (x-axis) × 25 units (y-axis)

Each unit is typically 1cm (configurable with `--side-length`).

## Credits

- **labelroi**: [https://github.com/talmolab/labelroi](https://github.com/talmolab/labelroi)
- Developped for a NASA-funded project aiming to capture mouse pose and behavior in spaceflight [NASA grant 80NSSC24K0346](https://taskbook.nasaprs.com/tbp/index.cfm?action=public_query_taskbook_content&TASKID=16097)

## License

MIT License
