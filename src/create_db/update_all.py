import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.rename import ProgressTracker
from src.create_db import create_character_table, create_relation_table, create_rename_table
from src.create_db.update_image_table import UpdateImageTable
from src.utils.config_constant import AppSettings

if __name__ == '__main__':

    ## UpdateImageTable
    updater = UpdateImageTable(
        db_file=AppSettings.DB_FILE,
        image_dir=AppSettings.NEW_IMAGE_DIR,
        batch_size=1000,
        max_workers=4
    )
    updater.run()

    create_character_table.main()
    create_relation_table.main()
    create_rename_table.main()
    ## rename
    ProgressTracker.main()