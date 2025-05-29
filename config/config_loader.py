# config/config_loader.py
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
_config_cache = None

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config/config.yaml"

def load_config_yaml(path: Path = DEFAULT_CONFIG_PATH):
    """Load and cache YAML config, returning as dict."""
    global _config_cache
    if _config_cache:
        return _config_cache

    if not path.exists():
        logger.error(f"❌ Config file not found: {path}")
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    logger.info(f"✅ Loaded config from {path}")
    return _config_cache
