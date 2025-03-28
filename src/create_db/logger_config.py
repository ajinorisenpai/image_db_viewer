import logging
import os
from datetime import datetime
from typing import Optional


class LoggerConfig:
    """
    アプリケーション全体で使用できるロギング設定を提供するクラス
    """

    @staticmethod
    def setup_logger(
            logger_name: Optional[str] = None,
            log_level: int = logging.INFO,
            log_format: str = '%(asctime)s - %(levelname)s - %(message)s',
            log_file: Optional[str] = None,
            console_output: bool = True,
            console_level: int = logging.INFO,
            create_log_dir: bool = True
    ) -> logging.Logger:
        """
        ロガーを設定して返す

        Args:
            logger_name (str, optional): ロガー名。Noneの場合は__name__を使用
            log_level (int, optional): ロギングレベル。デフォルトはINFO
            log_format (str, optional): ログのフォーマット
            log_file (str, optional): ログファイルのパス。Noneの場合はファイル出力なし
            console_output (bool, optional): コンソール出力するかどうか
            console_level (int, optional): コンソール出力のログレベル
            create_log_dir (bool, optional): ログディレクトリが存在しない場合に作成するかどうか

        Returns:
            logging.Logger: 設定されたロガーオブジェクト
        """
        # ロガー名が指定されていない場合は呼び出し元のモジュール名を使用
        if logger_name is None:
            import inspect
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            logger_name = module.__name__

        # ロガーを取得
        logger: logging.Logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)

        # 既存のハンドラをクリア（二重登録防止）
        if logger.handlers:
            logger.handlers.clear()

        # ログファイルが指定されている場合
        if log_file:
            # ログディレクトリの作成
            if create_log_dir:
                log_dir: str = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir)

            # ファイルハンドラを追加
            file_handler: logging.FileHandler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter: logging.Formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        # コンソール出力が有効な場合
        if console_output:
            console_handler: logging.StreamHandler = logging.StreamHandler()
            console_handler.setLevel(console_level)
            console_formatter: logging.Formatter = logging.Formatter(log_format)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        return logger

    @staticmethod
    def get_default_logger(module_name: str, log_dir: str = 'logs') -> logging.Logger:
        """
        デフォルト設定のロガーを取得する

        Args:
            module_name (str): モジュール名
            log_dir (str, optional): ログディレクトリ

        Returns:
            logging.Logger: 設定されたロガーオブジェクト
        """
        # ログファイル名にタイムスタンプを含める
        timestamp: str = datetime.now().strftime('%Y%m%d')
        log_file: str = os.path.join(log_dir, f"{module_name}_{timestamp}.log")

        return LoggerConfig.setup_logger(
            logger_name=module_name,
            log_file=log_file,
            console_output=True
        )

    @staticmethod
    def get_batch_logger(batch_name: str, include_timestamp: bool = True) -> logging.Logger:
        """
        バッチ処理用のロガーを取得する

        Args:
            batch_name (str): バッチ処理名
            include_timestamp (bool, optional): ログファイル名にタイムスタンプを含めるかどうか

        Returns:
            logging.Logger: 設定されたロガーオブジェクト
        """
        log_dir: str = 'batch_logs'

        if include_timestamp:
            timestamp: str = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file: str = os.path.join(log_dir, f"{batch_name}_{timestamp}.log")
        else:
            log_file: str = os.path.join(log_dir, f"{batch_name}.log")

        return LoggerConfig.setup_logger(
            logger_name=f"batch.{batch_name}",
            log_file=log_file,
            log_format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            console_output=True
        )