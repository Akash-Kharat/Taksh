import { vi, describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { Dashboard } from '../pages/Dashboard';
import { systemApi } from '../services/api/systemApi';
import { healthApi } from '../services/api/healthApi';

vi.mock('../services/api/systemApi', () => ({
  systemApi: {
    getSystemInfo: vi.fn(),
    getReadiness: vi.fn(),
    getReleaseInfo: vi.fn(),
  },
}));

vi.mock('../services/api/healthApi', () => ({
  healthApi: {
    getHealth: vi.fn(),
  },
}));

describe('Dashboard Component', () => {
  it('renders loading spinner initially', () => {
    vi.mocked(systemApi.getSystemInfo).mockReturnValue(new Promise(() => {}));
    vi.mocked(systemApi.getReadiness).mockReturnValue(new Promise(() => {}));
    vi.mocked(healthApi.getHealth).mockReturnValue(new Promise(() => {}));
    vi.mocked(systemApi.getReleaseInfo).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<Dashboard />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders system info, readiness score, health cards, and release metadata when loaded', async () => {
    vi.mocked(systemApi.getSystemInfo).mockResolvedValue({
      version: '1.0.0',
      uptime_seconds: 7200, // 2 hours
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

    vi.mocked(healthApi.getHealth).mockResolvedValue({
      status: 'healthy',
      components: {
        database: 'healthy',
        vector_store: 'healthy',
        workspace: 'degraded',
      },
    });

    vi.mocked(systemApi.getReleaseInfo).mockResolvedValue({
      version: '1.0.0',
      schema_version: 'a1b2c3d4e5f6',
      build_date: '2026-06-23T12:00:00Z',
      milestones_completed: ['MS-01', 'MS-21'],
    });

    renderWithProviders(<Dashboard />);

    // Wait for content to render (we look for a key text field)
    const scoreText = await screen.findByText('95%');
    expect(scoreText).toBeTruthy();

    expect(screen.getByText('System Dashboard')).toBeTruthy();
    expect(screen.getAllByText(/Uptime:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('2h 0s').length).toBeGreaterThan(0);
    expect(screen.getAllByText('HEALTHY').length).toBeGreaterThan(0);

    // Check subsystem health
    expect(screen.getByText('database')).toBeTruthy();
    expect(screen.getByText('vector_store')).toBeTruthy();
    expect(screen.getByText('DEGRADED')).toBeTruthy();

    // Check release metadata card
    expect(screen.getByText('a1b2c3d4e5f6')).toBeTruthy();
    expect(screen.getByText('MS-21')).toBeTruthy();
  });
});
