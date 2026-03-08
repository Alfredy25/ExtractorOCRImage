"""Tests de crop_tools."""
import numpy as np
import pytest

from app.core.crop_tools import apply_crop, apply_rotation


def test_apply_crop():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[10:30, 20:60] = 255
    cropped = apply_crop(img, (20, 10, 40, 20))
    assert cropped.shape == (20, 40, 3)
    assert np.all(cropped == 255)


def test_apply_rotation_90():
    img = np.zeros((10, 20, 3), dtype=np.uint8)
    rotated = apply_rotation(img, 90)
    assert rotated.shape == (20, 10, 3)


def test_apply_rotation_minus90():
    img = np.zeros((10, 20, 3), dtype=np.uint8)
    rotated = apply_rotation(img, -90)
    assert rotated.shape == (20, 10, 3)


def test_apply_rotation_180():
    img = np.zeros((10, 20, 3), dtype=np.uint8)
    rotated = apply_rotation(img, 180)
    assert rotated.shape == (10, 20, 3)
