import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StartupGuard } from '../components/StartupGuard';

describe('StartupGuard Component', () => {
  it('renders loading view when loading and connecting', () => {
    render(
      <StartupGuard
        connectionState="CONNECTING"
        readiness={null}
        isLoading={true}
        onRetry={vi.fn()}
      >
        <div data-testid="child">Normal Content</div>
      </StartupGuard>
    );

    expect(screen.getByText('Connecting to Taksh backend...')).toBeTruthy();
    expect(screen.queryByTestId('child')).toBeNull();
  });

  it('renders backend offline screen when disconnected', () => {
    const mockRetry = vi.fn();
    render(
      <StartupGuard
        connectionState="DISCONNECTED"
        readiness={null}
        isLoading={false}
        onRetry={mockRetry}
      >
        <div data-testid="child">Normal Content</div>
      </StartupGuard>
    );

    expect(screen.getByText('Backend Offline')).toBeTruthy();
    expect(screen.queryByTestId('child')).toBeNull();

    const retryBtn = screen.getByText('Reconnect Now');
    fireEvent.click(retryBtn);
    expect(mockRetry).toHaveBeenCalled();
  });

  it('renders system not ready screen when readiness score is below 70', () => {
    const readiness = {
      status: 'not_ready' as const,
      score: 55,
      checks_passed: 5,
      checks_failed: 2,
      warnings: 0,
    };

    render(
      <StartupGuard
        connectionState="CONNECTED"
        readiness={readiness}
        isLoading={false}
        onRetry={vi.fn()}
      >
        <div data-testid="child">Normal Content</div>
      </StartupGuard>
    );

    expect(screen.getByText('System Not Ready')).toBeTruthy();
    expect(screen.getByText('55%')).toBeTruthy();
    expect(screen.queryByTestId('child')).toBeNull();
  });

  it('renders children normally when score is 70 or above', () => {
    const readiness = {
      status: 'degraded' as const,
      score: 75,
      checks_passed: 10,
      checks_failed: 0,
      warnings: 2,
    };

    render(
      <StartupGuard
        connectionState="CONNECTED"
        readiness={readiness}
        isLoading={false}
        onRetry={vi.fn()}
      >
        <div data-testid="child">Normal Content</div>
      </StartupGuard>
    );

    expect(screen.getByTestId('child')).toBeTruthy();
    expect(screen.queryByText('System Not Ready')).toBeNull();
  });
});
