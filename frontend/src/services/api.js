const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
let accessToken = '';

export function setAccessToken(token) {
  accessToken = token || '';
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getApiUrl() {
  return API_URL;
}

export function getMe() {
  return request('/me');
}

export function listOpportunities(filters = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return request(`/opportunities${query ? `?${query}` : ''}`);
}

export function createOpportunity(data) {
  return request('/opportunities', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateOpportunity(id, data) {
  return request(`/opportunities/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export function deleteOpportunity(id) {
  return request(`/opportunities/${id}`, {
    method: 'DELETE',
  });
}

export function listSearchRules() {
  return request('/search-rules');
}

export function listScanLogs(limit = 10) {
  return request(`/scan-logs?limit=${limit}`);
}

export function createScanLog(data) {
  return request('/scan-logs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}


export function runSetadAccessTest(data = {}) {
  return request('/setad/access-test', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
