import cv2
import numpy as np
from math import sqrt, ceil
from PIL import Image, ImageDraw, ImageFont


class ImageProcessor:
    """画像の基本処理を担当するクラス"""

    def __init__(self, font_size=16, font_color=(255, 255, 255),
                 text_opacity=192, bg_opacity=128):
        self.font_size = font_size
        self.font_color = font_color
        self.text_opacity = text_opacity
        self.bg_opacity = bg_opacity
        self.font = self._load_font()

    def _load_font(self):
        """利用可能なフォントを読み込み"""
        try:
            return ImageFont.truetype("C:/Users/thund/AppData/Local/Microsoft/Windows/Fonts/x12y16pxMaruMonica.ttf",self.font_size)

        except IOError:
            return ImageFont.load_default()

    def resize_image(self, img, target_size):
        """アスペクト比を維持したまま画像をリサイズし、余白を白で埋める"""
        # NumPy配列からPIL Imageに変換（必要な場合）
        pil_img = Image.fromarray(img) if isinstance(img, np.ndarray) else img

        # 元のサイズとアスペクト比を取得
        orig_width, orig_height = pil_img.size
        orig_aspect = orig_width / orig_height

        # ターゲットのサイズとアスペクト比
        target_width, target_height = target_size
        target_aspect = target_width / target_height

        # アスペクト比を維持したリサイズサイズを計算
        if orig_aspect > target_aspect:
            # 画像が横長の場合は幅に合わせる
            resize_width = target_width
            resize_height = int(resize_width / orig_aspect)
        else:
            # 画像が縦長の場合は高さに合わせる
            resize_height = target_height
            resize_width = int(resize_height * orig_aspect)

        # 画像をリサイズ
        resized_img = pil_img.resize((resize_width, resize_height), Image.LANCZOS)

        # 新しい白いキャンバスを作成
        new_img = Image.new(pil_img.mode, target_size,
                            (255, 255, 255, 255) if pil_img.mode == 'RGBA' else (255, 255, 255))

        # リサイズした画像を中央に配置
        paste_x = (target_width - resize_width) // 2
        paste_y = (target_height - resize_height) // 2

        # アルファチャンネルがある場合はマスクを使用して配置
        if pil_img.mode == 'RGBA':
            new_img.paste(resized_img, (paste_x, paste_y), resized_img)
        else:
            new_img.paste(resized_img, (paste_x, paste_y))

        # 結果を返す（元がNumPy配列の場合は変換して返す）
        return new_img if not isinstance(img, np.ndarray) else np.array(new_img)

    def add_label(self, img, label):
        """画像に半透明のラベルを追加（中央下に配置）"""
        # PILイメージに変換
        pil_img = Image.fromarray(img) if isinstance(img, np.ndarray) else img

        # RGBA変換
        if pil_img.mode != 'RGBA':
            pil_img = pil_img.convert('RGBA')

        # 透明レイヤー作成
        overlay = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # ラベルのサイズと位置を計算
        temp_pos = (0, 0)
        bbox = draw.textbbox(temp_pos, label, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 中央下の位置を計算
        img_width, img_height = pil_img.size
        margin = 10
        text_pos = ((img_width - text_width) // 2, img_height - text_height - margin)

        # 背景と文字を描画
        bbox = draw.textbbox(text_pos, label, font=self.font)
        draw.rectangle(
            [bbox[0] - 5, bbox[1] - 5, bbox[2] + 5, bbox[3] + 5],
            fill=(0, 0, 0, self.bg_opacity)
        )

        # フォントカラーにアルファを追加
        font_color = self.font_color + (self.text_opacity,) if len(self.font_color) == 3 else self.font_color

        draw.text(text_pos, label, font=self.font, fill=font_color)

        # 合成して返す
        result = Image.alpha_composite(pil_img, overlay)
        return np.array(result) if isinstance(img, np.ndarray) else result
