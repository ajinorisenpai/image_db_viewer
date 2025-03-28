from configparser import ConfigParser


class AppSettings:
    _config = ConfigParser()
    _config.read('C:/Users/thund/source/notebook/nai/config.ini')

    DB_FILE = _config.get('CONSTANTS', 'DB_FILE')
    NEW_IMAGE_DIR = _config.get('CONSTANTS', 'NEW_IMAGE_DIR')
    FONT_PATH = _config.get('CONSTANTS', 'FONT_PATH')
    SQL_DIR = _config.get('CONSTANTS', 'SQL_DIR')

    @classmethod
    def get_int(cls, section, key, fallback=None):
        return cls._config.getint(section, key, fallback=fallback)

    @classmethod
    def get_float(cls, section, key, fallback=None):
        return cls._config.getfloat(section, key, fallback=fallback)

    @classmethod
    def get_boolean(cls, section, key, fallback=None):
        return cls._config.getboolean(section, key, fallback=fallback)
