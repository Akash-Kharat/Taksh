import { apiClient } from './client';
import { HealthResponse } from '../../types/backend';

export const healthApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/api/v1/health');
    return response.data;
  },
};
