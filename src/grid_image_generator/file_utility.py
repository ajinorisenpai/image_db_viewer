import os

import cv2
import numpy as np
from math import sqrt, ceil
from PIL import Image, ImageDraw, ImageFont

def load_images(file_paths, thumbnail_size=None):
    """画像ファイルを読み込む"""
    images = []
    for path in file_paths:
        if path.lower().endswith(('.png', '.jpg', '.jpeg')):
            # PNG画像はRGBAモードで読み込み
            img = Image.open(path)
            if path.lower().endswith('.png'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            img.thumbnail((1216 // 4, 832 // 4))
            images.append(img)
    return images


def display_grid(grid):
    """OpenCVでグリッド画像を表示"""
    # NumPy配列に変換
    if not isinstance(grid, np.ndarray):
        grid = np.array(grid)

    # RGBA画像の場合、背景と合成
    if grid.shape[2] == 4:
        background = np.ones((grid.shape[0], grid.shape[1], 3), dtype=np.uint8) * 255
        alpha = grid[:, :, 3:4] / 255.0
        rgb = grid[:, :, :3]
        display_img = (rgb * alpha + background * (1 - alpha)).astype(np.uint8)
    else:
        display_img = grid

    # BGR変換して表示
    cv2.imshow('Image Grid', cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def save_grid(grid, output_path):
    """グリッド画像を保存"""
    # PIL Image変換
    if isinstance(grid, np.ndarray):
        grid = Image.fromarray(grid)

    # 拡張子に応じた保存
    if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
        if grid.mode == 'RGBA':
            grid = grid.convert('RGB')
        grid.save(output_path, quality=95)
    else:
        if not output_path.lower().endswith('.png'):
            output_path += '.png'
        grid.save(output_path)
    print(f"保存しました: {output_path}")


def get_unique_filename(filepath):
    """既存ファイルと重複しないファイル名を生成する関数
    同名ファイルがある場合は_1, _2などの連番を付ける
    """
    if not os.path.exists(filepath):
        return filepath

    name, ext = os.path.splitext(filepath)
    i = 1
    while True:
        new_name = f"{name[:-1]}{i}"
        if not os.path.exists(new_name+ext):
            return new_name
        i += 1