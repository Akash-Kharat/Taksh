import { vi, describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { Settings } from '../pages/Settings';
import { systemApi } from '../services/api/systemApi';

vi.mock('../services/api/systemApi', () => ({
  systemApi: {
    getSystemConfig: vi.fn(),
  },
}));

describe('Settings Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders loading states initially', () => {
    vi.mocked(systemApi.getSystemConfig).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<Settings />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders system configurations snapshot and backend URL input when loaded', async () => {
    vi.mocked(systemApi.getSystemConfig).mockResolvedValue({
      version: '1.0.0',
      environment: 'production',
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

    renderWithProviders(<Settings />);

    const header = await screen.findByText('System Settings');
    expect(header).toBeTruthy();

    expect(screen.getByText('Backend Connection Setup')).toBeTruthy();
    expect(screen.getByText('Active Core Config Snapshot')).toBeTruthy();

    // Check config details
    expect(screen.getByText('production')).toBeTruthy();
    expect(screen.getByText('8000')).toBeTruthy();
    expect(screen.getByText('5000 chars')).toBeTruthy();
  });

  it('allows saving and resetting BACKEND_URL override in localStorage', async () => {
    vi.mocked(systemApi.getSystemConfig).mockResolvedValue({
      version: '1.0.0',
      environment: 'production',
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

    // Mock window.location.reload
    const mockReload = vi.fn();
    Object.defineProperty(window, 'location', {
      writable: true,
      configurable: true,
      value: {
        ...window.location,
        reload: mockReload,
      },
    });

    renderWithProviders(<Settings />);

    const input = await screen.findByPlaceholderText('e.g., http://127.0.0.1:8000') as HTMLInputElement;
    expect(input.value).toBe('http://127.0.0.1:8000'); // default fallback

    fireEvent.change(input, { target: { value: 'http://192.168.1.100:8000/' } });
    expect(input.value).toBe('http://192.168.1.100:8000/');

    const saveBtn = screen.getByText('Save Connection Settings');
    fireEvent.click(saveBtn);

    // Should store url normalized (without trailing slash)
    expect(localStorage.getItem('TAKSH_BACKEND_URL')).toBe('http://192.168.1.100:8000');

    await waitFor(() => {
      expect(mockReload).toHaveBeenCalled();
    });
  });
});
