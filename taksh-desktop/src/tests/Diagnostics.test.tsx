import { vi, describe, it, expect } from 'vitest';

import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { Diagnostics } from '../pages/Diagnostics';
import { systemApi } from '../services/api/systemApi';
import { healthApi } from '../services/api/healthApi';
import { providerApi } from '../services/api/providerApi';

vi.mock('../services/api/systemApi', () => ({
  systemApi: {
    getMetrics: vi.fn(),
    getSystemInfo: vi.fn(),
    getReadiness: vi.fn(),
  },
}));

vi.mock('../services/api/healthApi', () => ({
  healthApi: {
    getHealth: vi.fn(),
  },
}));

vi.mock('../services/api/providerApi', () => ({
  providerApi: {
    getProvidersInfo: vi.fn(),
  },
}));

describe('Diagnostics Component', () => {
  it('renders loading states initially', () => {
    vi.mocked(systemApi.getMetrics).mockReturnValue(new Promise(() => {}));
    vi.mocked(healthApi.getHealth).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<Diagnostics />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders subsystem checks, latency, and telemetry counts when loaded', async () => {
    vi.mocked(systemApi.getMetrics).mockResolvedValue({
      conversation_count: 5,
      turn_count: 24,
      provider_requests: 10,
      provider_failures: 1,
      tool_executions: 12,
      memory_recalls: 18,
      knowledge_searches: 8,
      average_latency_ms: 124.5,
      active_sessions: 2,
    });

    vi.mocked(healthApi.getHealth).mockResolvedValue({
      status: 'healthy',
      components: {
        database: 'healthy',
        vector_store: 'healthy',
      },
    });

    renderWithProviders(<Diagnostics />);

    const header = await screen.findByText('System Diagnostics');
    expect(header).toBeTruthy();

    expect(screen.getByText('124.5ms')).toBeTruthy();
    expect(screen.getByText('24')).toBeTruthy(); // turns
    expect(screen.getByText('10.0%')).toBeTruthy(); // failure rate

    // Check table rows
    expect(screen.getByText('Active WebSocket Sessions')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
    expect(screen.getByText('Tool Executions')).toBeTruthy();
    expect(screen.getByText('12')).toBeTruthy();
    expect(screen.getByText('Memory Recalls (RAG)')).toBeTruthy();
    expect(screen.getByText('18')).toBeTruthy();
  });

  it('triggers local diagnostics JSON file download on export click', async () => {
    vi.mocked(systemApi.getMetrics).mockResolvedValue({
      conversation_count: 5,
      turn_count: 24,
      provider_requests: 10,
      provider_failures: 1,
      tool_executions: 12,
      memory_recalls: 18,
      knowledge_searches: 8,
      average_latency_ms: 124.5,
      active_sessions: 2,
    });

    vi.mocked(healthApi.getHealth).mockResolvedValue({
      status: 'healthy',
      components: {
        database: 'healthy',
      },
    });

    vi.mocked(systemApi.getSystemInfo).mockResolvedValue({
      version: '1.0.0',
      uptime_seconds: 7200,
      active_runtime_sessions: 3,
      active_voice_sessions: 1,
      active_provider_sessions: 2,
      memory_episodes: 15,
      open_tasks: 4,
      metrics_snapshots: 5,
      health: 'healthy',
    });

    vi.mocked(systemApi.getReadiness).mockResolvedValue({
      status: 'ready',
      score: 95,
      checks_passed: 12,
      checks_failed: 0,
      warnings: 1,
    });

    vi.mocked(providerApi.getProvidersInfo).mockResolvedValue({
      active_provider: 'gemini_live',
      provider_state: 'active',
      healthy: true,
      fallback_active: false,
      active_sessions: 2,
      reconnect_count: 0,
      failure_count: 0,
    });

    // Mock URL.createObjectURL and link.click
    const mockCreateObjectURL = vi.fn().mockReturnValue('mock-blob-url');
    const mockRevokeObjectURL = vi.fn();
    window.URL.createObjectURL = mockCreateObjectURL;
    window.URL.revokeObjectURL = mockRevokeObjectURL;

    renderWithProviders(<Diagnostics />);

    const exportBtn = await screen.findByText('Export Diagnostics');
    expect(exportBtn).toBeTruthy();

    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(mockCreateObjectURL).toHaveBeenCalled();
    });
  });
});
