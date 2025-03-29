import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.image_viewer.image_database_model import ImageDatabaseModel
from src.image_viewer.image_viewer_view import ImageViewerView
from src.image_viewer.image_viewer_viewmodel import ImageViewerViewModel
from src.utils.config_constant import AppSettings

def main():
    model = ImageDatabaseModel(AppSettings.DB_FILE)
    view_model = ImageViewerViewModel(model)
    view = ImageViewerView(view_model)
    view.setup_ui()

    view.show()


if __name__ == "__main__":
    main()