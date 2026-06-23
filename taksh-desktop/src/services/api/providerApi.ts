import { apiClient } from './client';
import { ProviderInfoResponse } from '../../types/backend';

export const providerApi = {
  getProvidersInfo: async (): Promise<ProviderInfoResponse> => {
    const response = await apiClient.get<ProviderInfoResponse>('/api/v1/providers/info');
    return response.data;
  },
};
