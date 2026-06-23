import { vi, describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { Providers } from '../pages/Providers';
import { providerApi } from '../services/api/providerApi';
import { systemApi } from '../services/api/systemApi';

vi.mock('../services/api/providerApi', () => ({
  providerApi: {
    getProvidersInfo: vi.fn(),
  },
}));

vi.mock('../services/api/systemApi', () => ({
  systemApi: {
    getSystemConfig: vi.fn(),
  },
}));

describe('Providers Component', () => {
  it('renders loading states initially', () => {
    vi.mocked(providerApi.getProvidersInfo).mockReturnValue(new Promise(() => {}));
    vi.mocked(systemApi.getSystemConfig).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<Providers />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders provider info blocks and log card when loaded', async () => {
    vi.mocked(providerApi.getProvidersInfo).mockResolvedValue({
      active_provider: 'gemini_live',
      provider_state: 'active',
      healthy: true,
      fallback_active: false,
      active_sessions: 2,
      reconnect_count: 1,
      failure_count: 0,
    });

    vi.mocked(systemApi.getSystemConfig).mockResolvedValue({
      version: '1.0.0',
      environment: 'development',
      providers: {
        llm: 'mock',
        stt: 'mock',
        tts: 'mock',
        realtime: 'gemini_live',
      },
      api_v1_prefix: '/api/v1',
      host: '127.0.0.1',
      port: 8000,
      log_level: 'INFO',
      enable_provider_health_checks: true,
      max_prompt_chars: 5000,
      max_knowledge_chunks: 5,
      max_memory_items: 10,
      max_episodes: 100,
      health_check_timeout_seconds: 30,
    });

    renderWithProviders(<Providers />);

    const header = await screen.findByText('Provider Diagnostics');
    expect(header).toBeTruthy();

    // Check configured engine text
    expect(screen.getByText('Realtime Channel')).toBeTruthy();
    expect(screen.getByText('GEMINI_LIVE')).toBeTruthy();

    expect(screen.getByText('Speech-To-Text (STT)')).toBeTruthy();
    expect(screen.getByText('Text-To-Speech (TTS)')).toBeTruthy();

    // Check realtime status
    expect(screen.getByText('active')).toBeTruthy();
    expect(screen.getByText('CONNECTED')).toBeTruthy(); // Health status: CONNECTED

    // Check provider log card counters
    expect(screen.getByText('Connection Attempts')).toBeTruthy();
    expect(screen.getByText('Total Failure Traces')).toBeTruthy();
    expect(screen.getByText('Active Clients (STT/TTS)')).toBeTruthy();
  });
});
