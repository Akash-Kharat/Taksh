import { vi, describe, it, expect } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { MessageBubble } from '../components/MessageBubble';

describe('MessageBubble Component', () => {
  it('renders User message bubble correctly', () => {
    renderWithProviders(
      <MessageBubble role="user" content="Tell me a joke" timestamp="2026-06-23T12:00:00Z" />
    );
    expect(screen.getByText('Tell me a joke')).toBeTruthy();
  });

  it('renders Assistant message bubble with markdown formatting securely', () => {
    const markdownContent = '# Heading\n- Item 1\n- Item 2\n\n```python\nprint("hello")\n```';
    renderWithProviders(
      <MessageBubble role="assistant" content={markdownContent} timestamp="2026-06-23T12:00:05Z" />
    );

    // Verify markdown elements render
    expect(screen.getByRole('heading', { level: 1 })).toBeTruthy();
    expect(screen.getByText('Item 1')).toBeTruthy();
    
    // Verify custom code block renders
    expect(screen.getByText('python')).toBeTruthy();
    expect(screen.getByText('print("hello")')).toBeTruthy();
  });

  it('hides raw html content securely', () => {
    const maliciousContent = 'Hello <script>alert("malicious")</script> world <div id="injected">HTML</div>';
    renderWithProviders(
      <MessageBubble role="assistant" content={maliciousContent} />
    );
    
    // Raw HTML tag should not render (or text within custom tags should be skipped if skipHtml is active)
    expect(screen.queryByText('HTML')).toBeNull();
  });

  it('triggers diagnostics callback on click', () => {
    const mockSelectDiagnostics = vi.fn();
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="Response text"
        onSelectDiagnostics={mockSelectDiagnostics}
      />
    );

    const diagBtn = screen.getByText('• Turn Diagnostics');
    fireEvent.click(diagBtn);

    expect(mockSelectDiagnostics).toHaveBeenCalled();
  });
});
