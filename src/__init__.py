import importlib

from src.core.config import INSTALLED_APPS
from src.core.config import settings

for app in INSTALLED_APPS:
    try:
        importlib.import_module(f"{app}.{settings.MODELS_FILE_NAME[:-3]}")
    except ModuleNotFoundError as e:
        continue
