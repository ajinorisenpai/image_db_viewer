import dearpygui.dearpygui as dpg
import cv2
import threading
import queue
import time
import os


class ImageLoader:
    """画像読み込みとマルチスレッド処理を担当するクラス"""

    def __init__(self):
        self.image_queue = queue.Queue()
        self.loading_complete = threading.Event()
        self.stop_loading = threading.Event()
        self.worker_thread = None

    def load_folder(self, folder_path, status_callback=None):
        """指定フォルダ内の画像を読み込み、キューに追加"""
        # 以前のスレッドがあれば停止リクエスト
        self.stop_loading.set()
        if self.worker_thread and self.worker_thread.is_alive():
            time.sleep(0.2)  # スレッドが停止するのを少し待つ

        # 状態のリセット
        self.stop_loading.clear()
        self.loading_complete.clear()

        # 新しいワーカースレッドを開始
        self.worker_thread = threading.Thread(
            target=self._image_loader_thread,
            args=(folder_path, status_callback),
            daemon=True
        )
        self.worker_thread.start()

    def _image_loader_thread(self, folder_path, status_callback=None):
        """画像読み込みワーカースレッド"""
        # 画像ファイル拡張子
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']

        try:
            # フォルダ内の画像ファイルを取得
            image_files = [
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and
                   os.path.splitext(f.lower())[1] in image_extensions
            ]

            total_files = len(image_files)
            if status_callback:
                status_callback("total", total_files)

            for i, filename in enumerate(image_files):
                # 停止リクエストがあった場合は処理を中断
                if self.stop_loading.is_set():
                    break

                try:
                    file_path = os.path.join(folder_path, filename)
                    img = cv2.imread(file_path)
                    if img is None:
                        print(f"画像の読み込みに失敗しました: {file_path}")
                        continue

                    # RGBA形式に変換
                    img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

                    # サムネイル用に画像をリサイズ
                    height, width = img_rgba.shape[:2]
                    max_thumb_size = 100
                    if width > height:
                        thumb_width = max_thumb_size
                        thumb_height = int(height * max_thumb_size / width)
                    else:
                        thumb_height = max_thumb_size
                        thumb_width = int(width * max_thumb_size / height)

                    thumb = cv2.resize(img_rgba, (thumb_width, thumb_height))

                    # キューに情報を追加
                    self.image_queue.put({
                        'path': file_path,
                        'filename': filename,
                        'image': img_rgba,
                        'thumbnail': thumb,
                        'width': width,
                        'height': height
                    })

                    # 進捗状況を更新
                    if status_callback:
                        status_callback("progress", {
                            'current': i + 1,
                            'total': total_files,
                            'progress': (i + 1) / total_files
                        })

                    # UIの応答性を維持するため少し待機
                    time.sleep(0.01)

                except Exception as e:
                    print(f"画像処理エラー: {e} - {filename}")

            # 読み込み完了
            self.loading_complete.set()
            if not self.stop_loading.is_set() and status_callback:
                status_callback("complete", total_files)
            elif self.stop_loading.is_set() and status_callback:
                status_callback("cancelled", None)

        except Exception as e:
            print(f"フォルダ読み込みエラー: {e}")
            if status_callback:
                status_callback("error", str(e))
            self.loading_complete.set()