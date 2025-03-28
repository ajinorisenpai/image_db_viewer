from ImageLoader import ImageLoader
from ImageViewUI import ImageViewUI


class ImageViewerApp:
    """アプリケーション全体を管理するクラス"""

    def __init__(self, font_path=None):
        self.image_loader = ImageLoader()
        self.image_view_ui = ImageViewUI(self.image_loader)
        self.font_path = font_path

    def run(self):
        """アプリケーションの実行"""
        self.image_view_ui.setup_ui(self.font_path)
        self.image_view_ui.run()


# メイン実行部分
if __name__ == "__main__":
    # フォントパスを指定（
    font_path = "C:/Users/thund/AppData/Local/Microsoft/Windows/Fonts/x12y16pxMaruMonica.ttf"

    # アプリケーションの作成と実行
    app = ImageViewerApp(font_path)
    app.run()