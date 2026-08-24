from app.core.config import get_settings
from app.providers.interface import VPSProvider
from app.providers.custom_provider import CustomVPSProvider
from app.providers.mock_provider import MockVPSProvider

settings = get_settings()

_provider_instance: VPSProvider = None


def get_vps_provider() -> VPSProvider:
    global _provider_instance
    if _provider_instance is None:
        if settings.VPS_PROVIDER == "mock":
            _provider_instance = MockVPSProvider()
        else:
            _provider_instance = CustomVPSProvider()
    return _provider_instance


def set_vps_provider(provider: VPSProvider):
    global _provider_instance
    _provider_instance = provider