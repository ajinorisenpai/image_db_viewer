import cv2
import numpy as np
from math import sqrt, ceil
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt


class ImageGridGenerator:
    def __init__(self, max_rows=10, max_cols=10, font_size=10,
                 font_color=(255, 255, 255), add_numbers=True,
                 thumbnail_size=(1216 // 4, 832 // 4),
                 text_opacity=192, bg_opacity=128):
        # クラスフィールドの初期化
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.font_size = font_size
        self.font_color = font_color
        self.add_numbers = add_numbers
        self.thumbnail_size = thumbnail_size
        self.font = self._load_font()
        # 透明度の設定（0-255）
        self.text_opacity = text_opacity
        self.bg_opacity = bg_opacity

    def _validate_input(self, array):
        """入力データの検証"""
        if len(array) == 0:
            raise ValueError("画像が提供されていません")

        # チャンネル数を取得（RGBAの場合は4、RGBの場合は3）
        shape = array[0].shape
        if len(shape) == 3:
            height, width, channels = shape
        else:
            height, width = shape
            channels = 1

        return height, width, channels

    def _get_optimal_grid_size(self, num_images):
        """最適なグリッドサイズを計算"""
        optimal_cols = min(self.max_cols, ceil(sqrt(num_images)))
        optimal_rows = min(self.max_rows, ceil(num_images / optimal_cols))
        optimal_cols = min(self.max_cols, ceil(num_images / optimal_rows))
        return optimal_rows, optimal_cols

    def _load_font(self):
        """フォントの読み込み"""
        try:
            return ImageFont.truetype("C:/Users/thund/AppData/Local/Microsoft/Windows/Fonts/x12y16pxMaruMonica.ttf", self.font_size)
        except IOError:
            try:
                return ImageFont.truetype("DejaVuSans.ttf", self.font_size)
            except IOError:
                return ImageFont.load_default()

    def _resize_image(self, img, target_size):
        """画像のリサイズ処理"""
        pil_img = Image.fromarray(img)
        return pil_img.resize(target_size, Image.LANCZOS)

    def _add_number_to_image(self, img, number):
        """画像に番号を追加（中央下に配置、半透明）"""
        # NumPy配列からPIL Imageに変換
        pil_img = Image.fromarray(img)

        # RGBAモードに変換（重要）
        if pil_img.mode != 'RGBA':
            pil_img = pil_img.convert('RGBA')

        # 新しい透明レイヤーを作成
        txt_layer = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        # 画像サイズと番号テキストを設定
        img_width, img_height = pil_img.size
        number_text = str(number)

        # テキストのサイズを計算
        temp_position = (0, 0)
        left, top, right, bottom = draw.textbbox(temp_position, number_text, font=self.font)
        text_width = right - left
        text_height = bottom - top

        # 中央下の位置を計算
        margin = 10
        text_position = ((img_width - text_width) // 2, img_height - text_height - margin)

        # 新しい位置での背景ボックスを描画
        left, top, right, bottom = draw.textbbox(text_position, number_text, font=self.font)
        draw.rectangle(
            [left - 5, top - 5, right + 5, bottom + 5],
            fill=(0, 0, 0, self.bg_opacity)  # 背景の透明度を設定
        )

        # テキストを描画
        if isinstance(self.font_color, tuple) and len(self.font_color) == 3:
            font_color_with_alpha = self.font_color + (self.text_opacity,)  # 指定したアルファ値
        else:
            font_color_with_alpha = self.font_color

        draw.text(
            text_position,
            number_text,
            font=self.font,
            fill=font_color_with_alpha
        )

        # テキストレイヤーと元画像を合成
        result = Image.alpha_composite(pil_img, txt_layer)

        return np.array(result)

    def _create_blank_image(self, shape, channels=4):
        """空白画像の生成（RGBA対応）"""
        if channels == 4:
            # RGBA形式の空白画像（完全不透明の白）
            return np.ones((*shape, channels), dtype=np.uint8) * np.array([255, 255, 255, 255], dtype=np.uint8)
        else:
            # RGB形式の空白画像
            return np.ones((*shape, channels), dtype=np.uint8) * 255

    def _build_image_grid(self, processed_images, grid_size, target_size):
        """グリッド画像の構築（RGBA対応）"""
        grid_rows, grid_cols = grid_size
        target_height, target_width = target_size

        # RGBA画像を作成
        grid_image = np.zeros((grid_rows * target_height, grid_cols * target_width, 4), dtype=np.uint8)
        grid_image[:, :, :3] = 255  # RGB部分を白に初期化
        grid_image[:, :, 3] = 255  # アルファチャンネルを完全不透明に初期化

        # 画像をグリッドに配置
        for i, img in enumerate(processed_images):
            row = i // grid_cols
            col = i % grid_cols

            y_start = row * target_height
            y_end = y_start + target_height
            x_start = col * target_width
            x_end = x_start + target_width

            # アルファチャンネルも含めて配置
            if len(img.shape) == 3 and img.shape[2] == 4:  # RGBAの場合
                grid_image[y_start:y_end, x_start:x_end, :] = img
            elif len(img.shape) == 3 and img.shape[2] == 3:  # RGBの場合
                grid_image[y_start:y_end, x_start:x_end, :3] = img
            else:  # グレースケールの場合
                for c in range(3):
                    grid_image[y_start:y_end, x_start:x_end, c] = img

        return grid_image

    def create_grid(self, array):
        """画像の配列からグリッドを作成"""
        # 入力検証と基本情報取得
        target_height, target_width, channels = self._validate_input(array)
        num_images = len(array)
        target_size = (target_width, target_height)

        # グリッドサイズ計算
        grid_rows, grid_cols = self._get_optimal_grid_size(num_images)
        required_images = grid_rows * grid_cols

        # 画像処理パイプライン
        processed_images = []
        for idx, img in enumerate(array, 1):
            # リサイズ処理
            if img.shape[:2] != (target_height, target_width):
                pil_img = self._resize_image(img, target_size)
                img = np.array(pil_img)

            # 番号追加処理
            if self.add_numbers:
                img = self._add_number_to_image(img, idx)

            processed_images.append(img)

        # 不足分を空白画像で補完（RGBA対応）
        blank_image = self._create_blank_image((target_height, target_width), 4)  # RGBAで統一
        processed_images += [blank_image] * (required_images - len(processed_images))

        # グリッド画像の構築
        return self._build_image_grid(
            processed_images,
            (grid_rows, grid_cols),
            (target_height, target_width)
        )

    def pad_image(self, img, target_size=None):
        """画像をパディングして中央に配置（RGBA対応）"""
        if target_size is None:
            target_size = self.thumbnail_size

        # 元の画像モードを維持
        mode = img.mode

        # モードに応じて背景色を設定
        if mode == 'RGBA':
            background_color = (255, 255, 255, 255)  # 白（完全不透明）
        else:
            background_color = (255, 255, 255)  # 白

        new_img = Image.new(mode, target_size, color=background_color)
        paste_x = (target_size[0] - img.width) // 2
        paste_y = (target_size[1] - img.height) // 2

        if mode == 'RGBA':
            # 透過画像の場合はマスクを使用
            new_img.paste(img, (paste_x, paste_y), img)
        else:
            new_img.paste(img, (paste_x, paste_y))

        return new_img

    def load_and_resize_images(self, files):
        """画像ファイルを読み込んでリサイズ（RGBA対応）"""
        images = []
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                # PNGの場合はアルファチャンネルを保持、それ以外はRGBに変換
                if file.lower().endswith('.png'):
                    img = Image.open(file).convert('RGBA')
                else:
                    img = Image.open(file).convert('RGB')

                img.thumbnail(self.thumbnail_size)
                img = self.pad_image(img)
                images.append(np.asarray(img))
        return images

    def plot_images(self, image_files):
        """画像をグリッド状に配置して表示（OpenCV版、RGBA対応）"""
        images = self.load_and_resize_images(image_files)
        grid_image = self.create_grid(images)

        # グリッド画像のモードを確認
        if grid_image.shape[2] == 4:
            # RGBA画像の場合、アルファチャンネルを処理
            # 白い背景との合成
            background = np.ones((grid_image.shape[0], grid_image.shape[1], 3), dtype=np.uint8) * 255
            alpha = grid_image[:, :, 3:4] / 255.0
            rgb = grid_image[:, :, :3]
            grid_image_rgb = (rgb * alpha + background * (1 - alpha)).astype(np.uint8)

            # OpenCVはBGR形式で表示するため、RGB→BGR変換
            grid_image_bgr = cv2.cvtColor(grid_image_rgb, cv2.COLOR_RGB2BGR)
        else:
            # RGB画像の場合は単純にBGRに変換
            grid_image_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        # ウィンドウ名を設定して画像を表示
        window_name = 'Image Grid'
        cv2.imshow(window_name, grid_image_bgr)
        # キー入力を待機（0は無期限待機）
        cv2.waitKey(0)
        # ウィンドウを閉じる
        cv2.destroyAllWindows()

        return grid_image

    def save_grid(self, image_files, output_path, quality=95):
        """グリッド画像を生成して保存（PNG形式推奨）"""
        images = self.load_and_resize_images(image_files)
        grid_image = self.create_grid(images)

        # NumPyアレイからPIL Imageに変換
        pil_img = Image.fromarray(grid_image)

        # ファイル拡張子の確認
        if output_path.lower().endswith('.png'):
            pil_img.save(output_path, quality=quality)
        elif output_path.lower().endswith(('.jpg', '.jpeg')):
            # JPGの場合はRGBに変換してアルファチャンネルを破棄
            pil_img = pil_img.convert('RGB')
            pil_img.save(output_path, quality=quality)
        else:
            # 拡張子がない場合はPNGとして保存
            output_path += '.png'
            pil_img.save(output_path, quality=quality)

        print(f"グリッド画像を保存しました: {output_path}")
        return grid_image
