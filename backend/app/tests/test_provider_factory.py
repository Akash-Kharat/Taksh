import pytest
from app.services.providers.factory import provider_factory, ProviderFactory
from app.services.providers.contracts import SpeechToTextProvider, TextToSpeechProvider, RealtimeConversationProvider
from app.core.config import settings

def test_provider_factory_singleton():
    # Factory itself is a singleton
    factory1 = ProviderFactory()
    factory2 = provider_factory
    assert factory1 is factory2

def test_provider_factory_get_providers():
    # Clear cache first to start clean
    provider_factory.clear_cache()

    # Get STT provider
    stt1 = provider_factory.get_stt_provider("mock")
    stt2 = provider_factory.get_stt_provider("mock")
    assert stt1 is stt2
    assert isinstance(stt1, SpeechToTextProvider)

    # Get default STT provider when name is None
    stt_default = provider_factory.get_stt_provider()
    assert stt_default is stt1  # Since DEFAULT_STT_PROVIDER is "mock"

    # Get TTS provider
    tts1 = provider_factory.get_tts_provider("mock")
    tts2 = provider_factory.get_tts_provider("mock")
    assert tts1 is tts2
    assert isinstance(tts1, TextToSpeechProvider)

    # Get default TTS provider when name is None
    tts_default = provider_factory.get_tts_provider()
    assert tts_default is tts1

    # Get Realtime provider
    rt1 = provider_factory.get_realtime_provider("mock")
    rt2 = provider_factory.get_realtime_provider("mock")
    assert rt1 is rt2
    assert isinstance(rt1, RealtimeConversationProvider)

    # Get default Realtime provider when name is None
    from unittest.mock import patch
    with patch('app.core.config.settings.DEFAULT_REALTIME_PROVIDER', "mock"):
        rt_default = provider_factory.get_realtime_provider()
        assert rt_default is rt1

def test_provider_factory_clear_cache():
    provider_factory.clear_cache()
    
    stt1 = provider_factory.get_stt_provider("mock")
    provider_factory.clear_cache()
    stt2 = provider_factory.get_stt_provider("mock")
    
    assert stt1 is not stt2  # Cache was cleared, so a new instance is created
