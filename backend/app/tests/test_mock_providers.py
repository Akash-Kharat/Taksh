import pytest
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import ProviderState
from app.core.config import settings

@pytest.mark.anyio
async def test_mock_stt_provider():
    provider = provider_factory.get_stt_provider("mock")
    assert provider.get_state() == ProviderState.DISCONNECTED
    assert provider.is_connected() is False
    
    await provider.connect()
    assert provider.get_state() == ProviderState.CONNECTED
    assert provider.is_connected() is True

    transcript = await provider.transcribe_audio(b"some audio bytes")
    assert transcript == "mock transcript"

    await provider.disconnect()
    assert provider.get_state() == ProviderState.DISCONNECTED
    assert provider.is_connected() is False

@pytest.mark.anyio
async def test_mock_tts_provider():
    provider = provider_factory.get_tts_provider("mock")
    assert provider.get_state() == ProviderState.DISCONNECTED
    assert provider.is_connected() is False
    
    await provider.connect()
    assert provider.get_state() == ProviderState.CONNECTED
    assert provider.is_connected() is True

    audio_bytes = await provider.synthesize("hello world")
    assert len(audio_bytes) > 0

    await provider.disconnect()
    assert provider.get_state() == ProviderState.DISCONNECTED
    assert provider.is_connected() is False

@pytest.mark.anyio
async def test_mock_realtime_provider_queue_budget():
    provider = provider_factory.get_realtime_provider("mock")
    await provider.connect()
    await provider.start_session()
    
    assert provider.dropped_messages == 0
    
    max_size = settings.MAX_PROVIDER_QUEUE_SIZE
    # Send max_size + 5 text messages
    for i in range(max_size + 5):
        await provider.send_text(f"message {i}")
        
    assert len(provider.text_queue) == max_size
    assert provider.dropped_messages == 5
    
    # Check that oldest messages (0 to 4) were dropped
    first_item = await provider.receive_text()
    assert first_item == "message 5"
    
    # Verify same queue budget for audio
    provider.dropped_messages = 0
    for i in range(max_size + 10):
        await provider.send_audio(bytes([i]))
        
    assert len(provider.audio_queue) == max_size
    assert provider.dropped_messages == 10
    
    first_audio = await provider.receive_audio()
    assert first_audio == bytes([10])
    
    await provider.end_session()
    await provider.disconnect()
