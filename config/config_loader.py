import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_config_cache = None

def load_config_yaml(path="config/config.yaml"):
    """
    Load a YAML config file and return the parsed dictionary.
    Returns an empty dict if file is missing or malformed.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    
    resolved_path = Path(__file__).resolve().parent.parent / path

    if not resolved_path.exists():
        logger.error(f"❌ Config file not found: {resolved_path}")
        raise FileNotFoundError(f"Config file not found: {resolved_path}")

    with open(resolved_path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    logger.info(f"✅ Loaded config from {resolved_path}")
    return _config_cache