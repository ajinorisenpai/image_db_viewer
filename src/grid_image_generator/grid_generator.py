import cv2
import numpy as np
from math import sqrt, ceil
from PIL import Image, ImageDraw, ImageFont
import os
import image_processor as IP


class GridGenerator:
    """画像グリッドの生成を担当するクラス"""

    def __init__(self, max_grid_size=(10, 10), add_numbers=False):
        self.max_rows, self.max_cols = max_grid_size
        self.add_numbers = add_numbers  # 番号ではなくラベル表示に変更
        self.processor = IP.ImageProcessor()

    def _get_grid_dimensions(self, num_images):
        """最適なグリッドサイズを計算"""
        cols = min(self.max_cols, ceil(sqrt(num_images)))
        rows = min(self.max_rows, ceil(num_images / cols))
        cols = min(self.max_cols, ceil(num_images / rows))
        return rows, cols

    def create_grid(self, images, filenames=None):
        """画像リストからグリッド画像を生成

        Args:
            images: 画像リスト（PIL ImageまたはNumPy配列）
            filenames: 各画像に対応するファイル名のリスト（省略可）
        """
        if not images:
            raise ValueError("画像が提供されていません")

        # ファイル名が提供されていない場合、空の文字列で初期化
        if filenames is None:
            filenames = [""] * len(images)
        elif len(filenames) < len(images):
            # ファイル名が不足している場合は空文字で補完
            filenames = list(filenames) + [""] * (len(images) - len(filenames))

        # 画像サイズを統一（最初の画像に合わせる）
        first_img = images[0]
        if isinstance(first_img, np.ndarray):
            height, width = first_img.shape[:2]
            target_size = (width, height)
        else:  # PIL Image
            width, height = first_img.size
            target_size = (width, height)

        # グリッドサイズを計算
        rows, cols = self._get_grid_dimensions(len(images))

        # 画像を処理
        processed_images = []
        for i, (img, filename) in enumerate(zip(images, filenames)):
            # サイズ統一
            if isinstance(img, np.ndarray) and img.shape[:2] != (height, width):
                img = np.array(self.processor.resize_image(img, target_size))
            elif not isinstance(img, np.ndarray) and img.size != target_size:
                img = self.processor.resize_image(img, target_size)

            # ファイル名を表示（ファイル名がある場合のみ）
            if self.add_numbers:
                img = self.processor.add_label(img, str(i + 1))
            elif filename:
                # ベースファイル名のみ取得（パスを除去）
                base_filename = os.path.basename(filename)
                # 拡張子を除去（オプション）
                base_filename = os.path.splitext(base_filename)[0]
                img = self.processor.add_label(img, base_filename)

            processed_images.append(img)

        # 空白画像で埋める
        if len(processed_images) < rows * cols:
            # 空白画像の生成（最初の処理済み画像と同じ形式）
            sample = processed_images[0]
            if isinstance(sample, np.ndarray):
                blank = np.ones(sample.shape, dtype=np.uint8) * 255
            else:  # PIL Image
                blank = Image.new(sample.mode, sample.size, (255, 255, 255, 255))

            processed_images += [blank] * (rows * cols - len(processed_images))

        # グリッド生成
        return self._build_grid(processed_images, rows, cols, height, width)

    def _build_grid(self, images, rows, cols, height, width):
        """処理済み画像からグリッドを構築"""
        # NumPy配列で処理
        is_numpy = isinstance(images[0], np.ndarray)
        channels = images[0].shape[2] if is_numpy else (4 if images[0].mode == 'RGBA' else 3)

        if is_numpy:
            # NumPy配列のグリッド作成
            grid = np.zeros((rows * height, cols * width, channels), dtype=np.uint8)
            if channels == 4:
                grid[:, :, 3] = 255  # アルファチャンネルを不透明に

            # 画像を配置
            for i, img in enumerate(images):
                r, c = divmod(i, cols)
                y_start = r * height
                x_start = c * width
                grid[y_start:y_start + height, x_start:x_start + width] = img

            return grid
        else:
            # PIL画像のグリッド作成
            mode = images[0].mode
            grid = Image.new(mode, (cols * width, rows * height),
                             (255, 255, 255, 255) if mode == 'RGBA' else (255, 255, 255))

            # 画像を配置
            for i, img in enumerate(images):
                r, c = divmod(i, cols)
                grid.paste(img, (c * width, r * height),
                           img if mode == 'RGBA' else None)

            return grid
