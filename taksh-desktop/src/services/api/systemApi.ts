import { apiClient } from './client';
import {
  SystemInfoResponse,
  ReadinessResponse,
  SystemConfigResponse,
  ReleaseManifestResponse,
  MetricsResponse,
} from '../../types/backend';

export const systemApi = {
  getSystemInfo: async (): Promise<SystemInfoResponse> => {
    const response = await apiClient.get<SystemInfoResponse>('/api/v1/system/info');
    return response.data;
  },

  getReadiness: async (): Promise<ReadinessResponse> => {
    const response = await apiClient.get<ReadinessResponse>('/api/v1/system/readiness');
    return response.data;
  },

  getSystemConfig: async (): Promise<SystemConfigResponse> => {
    const response = await apiClient.get<SystemConfigResponse>('/api/v1/system/config');
    return response.data;
  },

  getReleaseInfo: async (): Promise<ReleaseManifestResponse> => {
    const response = await apiClient.get<ReleaseManifestResponse>('/api/v1/system/release');
    return response.data;
  },

  getMetrics: async (): Promise<MetricsResponse> => {
    const response = await apiClient.get<MetricsResponse>('/api/v1/metrics');
    return response.data;
  },
};
