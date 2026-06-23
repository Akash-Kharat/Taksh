import { vi, describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { ConversationSidebar } from '../components/ConversationSidebar';
import { ConversationSessionResponse } from '../types/backend';

describe('ConversationSidebar Component', () => {
  const mockSessions: ConversationSessionResponse[] = [
    {
      runtime_session_id: 'sess-today',
      conversation_title: 'Today Chat',
      conversation_session_state: 'active',
      started_at: new Date().toISOString(),
      last_message: 'Hello today'
    },
    {
      runtime_session_id: 'sess-yesterday',
      conversation_title: 'Yesterday Chat',
      conversation_session_state: 'closed',
      started_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      last_message: 'Hello yesterday'
    },
    {
      runtime_session_id: 'sess-older',
      conversation_title: 'Older Chat',
      conversation_session_state: 'closed',
      started_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      last_message: 'Hello older'
    }
  ];

  const mockSelectSession = vi.fn();
  const mockNewConversation = vi.fn();
  const mockPageChange = vi.fn();

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('groups and renders conversations by date categories', () => {
    renderWithProviders(
      <ConversationSidebar
        sessions={mockSessions}
        activeSessionId="sess-today"
        onSelectSession={mockSelectSession}
        onNewConversation={mockNewConversation}
        currentPage={1}
        totalSessions={3}
        pageSize={15}
        onPageChange={mockPageChange}
      />
    );

    expect(screen.getByText('Today')).toBeTruthy();
    expect(screen.getByText('Yesterday')).toBeTruthy();
    expect(screen.getByText('Older')).toBeTruthy();

    expect(screen.getByText('Today Chat')).toBeTruthy();
    expect(screen.getByText('Yesterday Chat')).toBeTruthy();
    expect(screen.getByText('Older Chat')).toBeTruthy();
  });

  it('filters sessions using search query client-side', () => {
    renderWithProviders(
      <ConversationSidebar
        sessions={mockSessions}
        activeSessionId="sess-today"
        onSelectSession={mockSelectSession}
        onNewConversation={mockNewConversation}
        currentPage={1}
        totalSessions={3}
        pageSize={15}
        onPageChange={mockPageChange}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search chats...');
    fireEvent.change(searchInput, { target: { value: 'yesterday' } });

    expect(screen.getByText('Yesterday Chat')).toBeTruthy();
    expect(screen.queryByText('Today Chat')).toBeNull();
    expect(screen.queryByText('Older Chat')).toBeNull();
  });

  it('triggers page change callbacks on prev/next button clicks', () => {
    renderWithProviders(
      <ConversationSidebar
        sessions={mockSessions}
        activeSessionId="sess-today"
        onSelectSession={mockSelectSession}
        onNewConversation={mockNewConversation}
        currentPage={2}
        totalSessions={40} // total sessions 40, pageSize 15 means 3 pages
        pageSize={15}
        onPageChange={mockPageChange}
      />
    );

    const prevBtn = screen.getByTitle('Previous Page');
    const nextBtn = screen.getByTitle('Next Page');

    fireEvent.click(prevBtn);
    expect(mockPageChange).toHaveBeenCalledWith(1);

    fireEvent.click(nextBtn);
    expect(mockPageChange).toHaveBeenCalledWith(3);
  });
});
