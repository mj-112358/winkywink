import { config } from '../config';

const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
  };
};

export const api = {
  getCameras: async () => {
    const res = await fetch(`${config.apiBaseUrl}/api/cameras/`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch cameras');
    return res.json();
  },

  createCamera: async (camera: any) => {
    const res = await fetch(`${config.apiBaseUrl}/api/cameras/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(camera),
    });
    if (!res.ok) throw new Error('Failed to create camera');
    return res.json();
  },

  deleteCamera: async (id: string) => {
    const res = await fetch(`${config.apiBaseUrl}/api/cameras/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete camera');
    return res.json();
  },

  getZones: async () => {
    return []; // Return empty for now
  },

  getInsights: async (request: any) => {
    return {
      insights: [
        {
          title: "Sample Insight",
          description: "This is a placeholder insight",
          type: "trend"
        }
      ],
      generated_at: new Date().toISOString()
    };
  },
};
