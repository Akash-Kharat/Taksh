import axios from 'axios';
import { getBackendUrl } from '../backend';

export const apiClient = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to resolve base URL dynamically on every request
apiClient.interceptors.request.use(
  (config) => {
    config.baseURL = getBackendUrl();
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
