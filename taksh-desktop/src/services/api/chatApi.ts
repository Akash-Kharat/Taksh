import { apiClient } from './client';
import { ChatGenerateResponse } from '../../types/backend';

export interface StreamProvider {
  start(): Promise<void>;
  cancel(): void;
  onChunk(callback: (chunk: string) => void): void;
  onComplete(callback: (fullText: string) => void): void;
  onError(callback: (err: any) => void): void;
}

export class SimulatedStreamProvider implements StreamProvider {
  private query: string;
  private sessionId?: string;
  private provider?: string;
  private chunkCallback?: (chunk: string) => void;
  private completeCallback?: (fullText: string) => void;
  private errorCallback?: (err: any) => void;
  private intervalId?: any;
  private isCancelled = false;

  constructor(query: string, sessionId?: string, provider?: string) {
    this.query = query;
    this.sessionId = sessionId;
    this.provider = provider;
  }

  async start(): Promise<void> {
    try {
      const response = await apiClient.post<ChatGenerateResponse>('/chat/generate', {
        query: this.query,
        session_id: this.sessionId || null,
        provider: this.provider || null
      });

      if (this.isCancelled) return;

      const data = response.data;
      if (data.status === 'success' && data.content) {
        const words = data.content.split(' ');
        let i = 0;
        this.intervalId = setInterval(() => {
          if (this.isCancelled) {
            clearInterval(this.intervalId);
            return;
          }
          if (i < words.length) {
            const chunk = words[i] + (i === words.length - 1 ? '' : ' ');
            if (this.chunkCallback) {
              this.chunkCallback(chunk);
            }
            i++;
          } else {
            clearInterval(this.intervalId);
            if (this.completeCallback) {
              this.completeCallback(data.content);
            }
          }
        }, 50); // emit a word every 50ms for simulated stream
      } else {
        const errorMsg = data.content || 'Failed to generate response';
        if (this.errorCallback) {
          this.errorCallback(new Error(errorMsg));
        }
      }
    } catch (err) {
      if (this.errorCallback) {
        this.errorCallback(err);
      }
    }
  }

  cancel(): void {
    this.isCancelled = true;
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  onChunk(callback: (chunk: string) => void): void {
    this.chunkCallback = callback;
  }

  onComplete(callback: (fullText: string) => void): void {
    this.completeCallback = callback;
  }

  onError(callback: (err: any) => void): void {
    this.errorCallback = callback;
  }
}

export const chatApi = {
  generate: async (query: string, sessionId?: string, provider?: string): Promise<ChatGenerateResponse> => {
    const response = await apiClient.post<ChatGenerateResponse>('/chat/generate', {
      query,
      session_id: sessionId || null,
      provider: provider || null
    });
    return response.data;
  }
};
