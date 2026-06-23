import { vi, describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { ConversationPage } from '../pages/ConversationPage';
import { conversationApi } from '../services/api/conversationApi';

vi.mock('../services/api/conversationApi', () => ({
  conversationApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    start: vi.fn(),
    stop: vi.fn().mockResolvedValue({ status: 'stopped', runtime_session_id: 'sess-1' }),
    message: vi.fn()
  }
}));

describe('ConversationPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(conversationApi.stop).mockResolvedValue({ status: 'stopped', runtime_session_id: 'sess-1' });
  });

  it('renders splash view initially when no session is active', async () => {
    vi.mocked(conversationApi.listSessions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 15
    });

    renderWithProviders(<ConversationPage />);

    expect(await screen.findByText('Continuous Conversation Shell')).toBeTruthy();
    expect(screen.getByText('Create Conversation Session')).toBeTruthy();
  });

  it('loads session turns and renders message history when selected', async () => {
    vi.mocked(conversationApi.listSessions).mockResolvedValue({
      items: [
        {
          runtime_session_id: 'sess-1',
          conversation_title: 'Title 1',
          conversation_session_state: 'active',
          started_at: new Date().toISOString(),
          last_message: 'User query'
        }
      ],
      total: 1,
      page: 1,
      page_size: 15
    });

    vi.mocked(conversationApi.getSession).mockResolvedValue({
      turns: [
        {
          turn_id: 'turn-1',
          runtime_session_id: 'sess-1',
          user_text: 'User query',
          assistant_text: 'Assistant response',
          latency_ms: 1500,
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          segment_count: 2,
          response_truncated: false,
          message_version: 1
        }
      ],
      metrics: null,
      provider_info: null,
      interruptions: 0,
      session_summary: null
    });

    renderWithProviders(<ConversationPage />);

    // Click on the sidebar session item
    const sidebarItem = await screen.findByText('Title 1');
    fireEvent.click(sidebarItem);

    // Verify messages list - wait for the assistant response first
    expect(await screen.findByText('Assistant response')).toBeTruthy();
    expect(screen.getByPlaceholderText('Type your message to Taksh...')).toBeTruthy();
  });
});

