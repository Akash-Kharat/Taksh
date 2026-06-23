import { apiClient } from './client';
import {
  ConversationStartResponse,
  ConversationSessionDetailResponse,
  ConversationInfoResponse,
  PaginatedConversationSessionsResponse
} from '../../types/backend';

export const conversationApi = {
  start: async (voiceSessionId?: string): Promise<ConversationStartResponse> => {
    const response = await apiClient.post<ConversationStartResponse>('/conversation/start', {
      voice_session_id: voiceSessionId || null
    });
    return response.data;
  },

  message: async (runtimeSessionId: string, message: string): Promise<{ assistant_text: string; turn_id: string }> => {
    const response = await apiClient.post<{ assistant_text: string; turn_id: string }>('/conversation/message', {
      runtime_session_id: runtimeSessionId,
      message
    });
    return response.data;
  },

  stop: async (runtimeSessionId: string): Promise<{ status: string; runtime_session_id: string }> => {
    const response = await apiClient.post<{ status: string; runtime_session_id: string }>('/conversation/stop', {
      runtime_session_id: runtimeSessionId
    });
    return response.data;
  },

  getSession: async (id: string): Promise<ConversationSessionDetailResponse> => {
    const response = await apiClient.get<ConversationSessionDetailResponse>(`/conversation/session/${id}`);
    return response.data;
  },

  getInfo: async (): Promise<ConversationInfoResponse> => {
    const response = await apiClient.get<ConversationInfoResponse>('/conversation/info');
    return response.data;
  },

  listSessions: async (page = 1, pageSize = 25): Promise<PaginatedConversationSessionsResponse> => {
    const response = await apiClient.get<PaginatedConversationSessionsResponse>('/conversation/sessions', {
      params: {
        page,
        page_size: pageSize
      }
    });
    return response.data;
  }
};
