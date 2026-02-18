"""Coordinate transformation for undistorting tracking labels.

This module provides functions to transform tracking coordinates from
distorted video space to undistorted space, matching the video undistortion.

NOTE: This module only performs undistortion (not rectification).
Coordinates remain in pixel space after transformation.
"""

import cv2
import numpy as np
import sleap_io as sio
from pathlib import Path
from typing import Optional, Dict
from .calibration import load_calibration


def undistort_points(
    points: np.ndarray,
    K: np.ndarray,
    dist: np.ndarray,
    newK: np.ndarray
) -> np.ndarray:
    """
    Undistort 2D points using camera calibration parameters.

    This transforms points from the distorted image space to the undistorted
    image space, matching the transformation applied to video frames.

    Args:
        points: Points to undistort (N, 2) array of [x, y] coordinates
        K: Camera intrinsic matrix (3, 3)
        dist: Distortion coefficients (5,) or (1, 5)
        newK: New camera matrix after undistortion (3, 3)

    Returns:
        Undistorted points (N, 2) array

    Notes:
        - NaN values are preserved (coordinates with missing data)
        - Uses cv2.undistortPoints with the optimal new camera matrix
    """
    points = np.asarray(points, dtype=np.float32)

    # Track which points are valid (not NaN)
    valid_mask = np.isfinite(points).all(axis=1)

    # Create output array (copy input to preserve NaNs)
    output = points.copy()

    if valid_mask.any():
        # Undistort only valid points
        valid_points = points[valid_mask].reshape(-1, 1, 2)
        undistorted = cv2.undistortPoints(valid_points, K, dist, P=newK)
        output[valid_mask] = undistorted.reshape(-1, 2)

    return output


def transform_slp_coordinates(
    slp_input_path: str,
    slp_output_path: str,
    calibration_path: str,
    video_path_mapping: Optional[Dict[str, str]] = None,
    undistorted_video_suffix: str = "_undistorted"
) -> None:
    """
    Transform coordinates in a SLEAP .slp file to match undistorted videos.

    This function:
    1. Loads the SLEAP labels file
    2. Loads calibration parameters from SpaceCage calibration
    3. Transforms all coordinates using undistortion (no rectification)
    4. Updates video file paths to point to undistorted videos
    5. Saves the transformed labels

    Args:
        slp_input_path: Path to input SLEAP .slp file
        slp_output_path: Path to output SLEAP .slp file
        calibration_path: Path to SpaceCage calibration YAML file
        video_path_mapping: Optional dict mapping original video names to undistorted ones
                           If None, automatically adds suffix to video filenames
        undistorted_video_suffix: Suffix to add to video names if video_path_mapping is None

    Example:
        >>> transform_slp_coordinates(
        ...     "labels.slp",
        ...     "labels_undistorted.slp",
        ...     "calibration.yml"
        ... )
    """
    print(f"Loading SLEAP labels from: {slp_input_path}")
    labels = sio.load_slp(slp_input_path)

    # Remove predictions if present (only transform ground truth)
    #labels.remove_predictions()

    print(f"Loading calibration from: {calibration_path}")
    K, dist, image_size, rms_error = load_calibration(calibration_path)

    # Get newK for undistortion (same as video undistortion pipeline)
    w, h = image_size
    newK, _ = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), alpha=1.0, newImgSize=(w, h))

    print(f"Calibration loaded (RMS error: {rms_error:.4f} pixels)")
    print(f"Image size: {w}x{h}")

    # Build video path mapping if not provided
    if video_path_mapping is None:
        video_path_mapping = {}
        for video in labels.videos:
            original_path = Path(video.filename)
            new_name = f"{original_path.stem}{undistorted_video_suffix}{original_path.suffix}"
            new_path = original_path.parent / new_name
            video_path_mapping[video.filename] = str(new_path)

    # Update video filenames
    print("Updating video file paths...")
    labels.replace_filenames(video_path_mapping)

    # Transform coordinates for each labeled frame
    print(f"Transforming coordinates for {len(labels)} labeled frames...")
    frames_transformed = 0
    points_transformed = 0

    for labeled_frame in labels:
        for instance in labeled_frame:
            # Get points array
            points = np.asarray(instance.points["xy"], dtype=np.float32)

            # Undistort points
            undistorted_points = undistort_points(points, K, dist, newK)

            # Update instance with transformed points
            instance.points["xy"] = undistorted_points

            # Count valid points
            valid_count = np.isfinite(undistorted_points).all(axis=1).sum()
            points_transformed += valid_count

        frames_transformed += 1

    # Save transformed labels
    print(f"Saving transformed labels to: {slp_output_path}")
    labels.save(slp_output_path)

    print(f"\nTransformation complete!")
    print(f"  Frames processed: {frames_transformed}")
    print(f"  Points transformed: {points_transformed}")
    print(f"  Output saved to: {slp_output_path}")


def batch_transform_slp_files(
    slp_files: list,
    calibration_path: str,
    output_dir: str,
    output_suffix: str = "_undistorted",
    video_path_mapping: Optional[Dict[str, str]] = None
) -> None:
    """
    Transform multiple SLEAP files using the same calibration.

    Args:
        slp_files: List of input .slp file paths
        calibration_path: Path to SpaceCage calibration YAML file
        output_dir: Directory to save transformed .slp files
        output_suffix: Suffix to add to output filenames
        video_path_mapping: Optional dict mapping video paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Batch transforming {len(slp_files)} SLEAP files...")
    print(f"Output directory: {output_dir}\n")

    for slp_path in slp_files:
        slp_path = Path(slp_path)
        output_path = output_dir / f"{slp_path.stem}{output_suffix}{slp_path.suffix}"

        print(f"\nProcessing: {slp_path.name}")
        print("-" * 60)

        try:
            transform_slp_coordinates(
                str(slp_path),
                str(output_path),
                calibration_path,
                video_path_mapping=video_path_mapping
            )
        except Exception as e:
            print(f"Error processing {slp_path.name}: {e}")
            continue

    print(f"\n{'=' * 60}")
    print("Batch transformation complete!")
    print(f"{'=' * 60}")
