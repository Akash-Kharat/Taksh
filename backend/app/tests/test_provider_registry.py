import pytest
from app.services.providers.registry import provider_registry
from app.services.providers.contracts import ProviderMetadata

def test_provider_registry_lists():
    # Verify that mock providers are registered
    stt_providers = provider_registry.list_stt_providers()
    tts_providers = provider_registry.list_tts_providers()
    realtime_providers = provider_registry.list_realtime_providers()

    assert "mock" in stt_providers
    assert "mock" in tts_providers
    assert "mock" in realtime_providers
    assert "gemini_live" in realtime_providers
    assert "openai_realtime" in realtime_providers

def test_provider_registry_resolve():
    # Resolve classes
    stt_cls = provider_registry.get_stt_provider_class("mock")
    tts_cls = provider_registry.get_tts_provider_class("mock")
    realtime_cls = provider_registry.get_realtime_provider_class("mock")
    
    assert stt_cls is not None
    assert tts_cls is not None
    assert realtime_cls is not None

    with pytest.raises(KeyError):
        provider_registry.get_stt_provider_class("nonexistent")

    with pytest.raises(KeyError):
        provider_registry.get_tts_provider_class("nonexistent")

    with pytest.raises(KeyError):
        provider_registry.get_realtime_provider_class("nonexistent")

def test_provider_registry_metadata():
    # Verify capability metadata on the resolved classes
    gemini_cls = provider_registry.get_realtime_provider_class("gemini_live")
    openai_cls = provider_registry.get_realtime_provider_class("openai_realtime")
    mock_rt_cls = provider_registry.get_realtime_provider_class("mock")

    # Instantiate to inspect metadata
    gemini_inst = gemini_cls()
    openai_inst = openai_cls()
    mock_rt_inst = mock_rt_cls()

    for inst, name in [(gemini_inst, "gemini_live"), (openai_inst, "openai_realtime"), (mock_rt_inst, "mock")]:
        meta = inst.get_metadata()
        assert isinstance(meta, ProviderMetadata)
        expected_name = "mock_realtime" if name == "mock" else name
        assert meta.provider_name == expected_name
        assert meta.provider_type == "realtime"
        assert meta.supports_streaming is True
        assert meta.supports_interruptions is True
