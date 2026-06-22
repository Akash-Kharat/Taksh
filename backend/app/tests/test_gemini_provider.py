import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.providers.gemini_live import GeminiLiveProvider
from app.services.providers.contracts import ProviderState
from app.core.config import settings
from app.models.database_models import ProviderSession, ProviderConversationMessage

@pytest.mark.anyio
async def test_gemini_provider_phase_a_text(db_session):
    provider = GeminiLiveProvider()
    provider.phase = "A"
    
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "serverContent": {
            "modelTurn": {
                "parts": [
                    {"text": "Hello, I am Gemini!"}
                ]
            }
        }
    })

    with patch('app.core.config.settings.GEMINI_API_KEY', "test-key"):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            
            await provider.connect(db=db_session)
            assert provider.get_state() == ProviderState.CONNECTED
            assert provider.provider_state == "active"
            assert provider.is_connected() is True
            
            await provider.start_session()
            
            # Send text
            await provider.send_text("Hello Gemini", db=db_session)
            assert provider.messages_sent == 1
            assert mock_ws.send.call_count == 2
            
            # Receive text
            response = await provider.receive_text(db=db_session)
            assert response == "Hello, I am Gemini!"
            assert provider.messages_received == 1
            
            # Verify database persistence
            db_session.expire_all()
            session_rec = db_session.query(ProviderSession).filter(
                ProviderSession.provider_session_id == provider.db_session_id
            ).first()
            assert session_rec is not None
            assert session_rec.messages_sent == 1
            assert session_rec.messages_received == 1
            
            messages = db_session.query(ProviderConversationMessage).filter(
                ProviderConversationMessage.provider_session_id == provider.db_session_id
            ).all()
            assert len(messages) == 2
            assert any(m.role == "user" and m.content == "Hello Gemini" for m in messages)
            assert any(m.role == "assistant" and m.content == "Hello, I am Gemini!" for m in messages)
            
            await provider.disconnect()


@pytest.mark.anyio
async def test_gemini_provider_budget_truncation(db_session):
    provider = GeminiLiveProvider()
    provider.phase = "A"
    
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "serverContent": {
            "modelTurn": {
                "parts": [{"text": "word "} for _ in range(60)]
            }
        }
    })

    with patch('app.core.config.settings.GEMINI_API_KEY', "test-key"):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            await provider.connect(db=db_session)
            await provider.start_session()
            
            response = await provider.receive_text(db=db_session)
            assert len(response.split()) == 50
            await provider.disconnect()


@pytest.mark.anyio
async def test_gemini_provider_phase_b_audio_input(db_session):
    provider = GeminiLiveProvider()
    provider.phase = "B"
    
    mock_ws = AsyncMock()
    with patch('app.core.config.settings.GEMINI_API_KEY', "test-key"):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            await provider.connect(db=db_session)
            await provider.start_session()
            
            valid_audio = b"\x00" * 512
            await provider.send_audio(valid_audio, db=db_session)
            assert provider.audio_frames_sent == 1
            
            invalid_audio = b"\x00" * 511
            with pytest.raises(ValueError):
                await provider.send_audio(invalid_audio, db=db_session)

            await provider.disconnect()


@pytest.mark.anyio
async def test_gemini_provider_phase_c_audio_output(db_session):
    provider = GeminiLiveProvider()
    provider.phase = "C"
    
    mock_ws = AsyncMock()
    import base64
    dummy_audio = b"\x01\x02\x03\x04"
    mock_ws.recv.return_value = json.dumps({
        "serverContent": {
            "modelTurn": {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "audio/pcm;rate=24000",
                            "data": base64.b64encode(dummy_audio).decode("utf-8")
                        }
                    }
                ]
            }
        }
    })

    with patch('app.core.config.settings.GEMINI_API_KEY', "test-key"):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            await provider.connect(db=db_session)
            await provider.start_session()
            
            audio_out = await provider.receive_audio(db=db_session)
            assert audio_out == dummy_audio
            assert provider.audio_frames_received == 1

            await provider.disconnect()
