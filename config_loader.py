import yaml
import logging

logger = logging.getLogger(__name__)

def load_config_yaml(path="config.yaml"):
    """
    Load a YAML config file and return the parsed dictionary.
    Returns an empty dict if file is missing or malformed.
    """
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
            logger.info(f"✅ Loaded config from {path}")
            return config
    except FileNotFoundError:
        logger.error(f"❌ Config file not found: {path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"❌ Error parsing YAML config: {e}")
        return {}