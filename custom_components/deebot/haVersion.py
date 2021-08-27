import logging

from awesomeversion import AwesomeVersion
from homeassistant.const import __version__ as HA_VERSION

_LOGGER = logging.getLogger(__name__)

MIN_REQUIRED_HA_VERSION = "2021.6.0"


def _is_equal_or_later(version: str) -> bool:
    return AwesomeVersion(HA_VERSION) >= version


def is_supported() -> bool:
    if _is_equal_or_later(MIN_REQUIRED_HA_VERSION):
        return True

    _LOGGER.error(f"Unsupported HA version! Please upgrade home assistant at least to \"{MIN_REQUIRED_HA_VERSION}\"")
    return False


def is_2021_9_or_later() -> bool:
    # Support at least until 2021.12 is out
    return _is_equal_or_later("2021.9.0")
