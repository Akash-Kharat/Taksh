import { vi, describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { CodeBlock } from '../components/CodeBlock';

describe('CodeBlock Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders language label and pre-formatted code block correctly', () => {
    renderWithProviders(<CodeBlock language="python" value="print('hello world')" />);

    expect(screen.getByText('python')).toBeTruthy();
    expect(screen.getByText("print('hello world')")).toBeTruthy();
    expect(screen.getByText('Copy')).toBeTruthy();
  });

  it('copies code text to clipboard on click', async () => {
    // Mock navigator.clipboard
    const mockWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      writable: true,
      configurable: true,
      value: {
        writeText: mockWriteText
      }
    });

    renderWithProviders(<CodeBlock language="javascript" value="const a = 10;" />);

    const copyBtn = screen.getByText('Copy');
    fireEvent.click(copyBtn);

    expect(mockWriteText).toHaveBeenCalledWith('const a = 10;');
    
    // Check state updates to Copied!
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeTruthy();
    });
  });
});
