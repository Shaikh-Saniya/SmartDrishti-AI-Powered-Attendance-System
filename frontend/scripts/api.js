/**
 * API Client — Centralized fetch wrapper for the FastAPI backend.
 * All endpoints are ready to connect once the backend is running.
 */

const API_BASE = 'http://localhost:8000/api/v1';

// ─── Token Management ───────────────────────────────────────────
function getToken() {
  return localStorage.getItem('auth_token');
}

function setToken(token) {
  localStorage.setItem('auth_token', token);
}

function removeToken() {
  localStorage.removeItem('auth_token');
}

function getUser() {
  const raw = localStorage.getItem('auth_user');
  return raw ? JSON.parse(raw) : null;
}

function setUser(user) {
  localStorage.setItem('auth_user', JSON.stringify(user));
}

function removeUser() {
  localStorage.removeItem('auth_user');
}

function isAuthenticated() {
  return !!getToken();
}

/**
 * Ensures the user is logged in. 
 * If not, redirects to login.html and returns false.
 */
function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

/**
 * Redirects to dashboard if already authenticated.
 * Used on login/signup pages.
 */
function redirectIfAuth() {
  if (isAuthenticated()) {
    window.location.href = 'dashboard.html';
  }
}

function logout() {
  removeToken();
  removeUser();
  window.location.href = 'login.html';
}


// ─── Fetch Wrapper ──────────────────────────────────────────────
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = getToken();

  const headers = options.headers || {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);

    if (response.status === 401) {
      logout();
      throw new Error('Session expired. Please login again.');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      let errorMsg = `Request failed (${response.status})`;
      
      if (error.message) {
        errorMsg = error.message;
      } else if (error.detail) {
        if (Array.isArray(error.detail)) {
          errorMsg = error.detail.map(e => `${e.loc ? e.loc.join('.') : 'Field'}: ${e.msg}`).join(' | ');
        } else {
          errorMsg = error.detail;
        }
      }
      throw new Error(errorMsg);
    }

    // Handle blob responses (Excel exports)
    const contentType = response.headers.get('content-type');
    if (contentType && (contentType.includes('spreadsheet') || contentType.includes('csv'))) {
      return response.blob();
    }

    return await response.json();
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}


// ─── Auth Endpoints ─────────────────────────────────────────────
const AuthAPI = {
  async login(email, password) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      let errorMsg = 'Login failed';
      if (error.message) {
        errorMsg = error.message;
      } else if (error.detail) {
        if (Array.isArray(error.detail)) {
          errorMsg = error.detail.map(e => `${e.loc ? e.loc.join('.') : 'Field'}: ${e.msg}`).join(' | ');
        } else {
          errorMsg = error.detail;
        }
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();
    setToken(data.access_token);
    return data;
  },

  async signup(name, email, password) {
    return apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ full_name: name, email, password }),
    });
  },

  async getProfile() {
    return apiRequest('/auth/me');
  },
};


// ─── Student Endpoints ──────────────────────────────────────────
const StudentAPI = {
  async list(page = 1, limit = 50, filters = {}) {
    const params = new URLSearchParams({ page, limit });
    if (filters.class) params.append('class', filters.class);
    if (filters.department) params.append('department', filters.department);
    if (filters.search) params.append('search', filters.search);
    return apiRequest(`/students?${params}`);
  },

  async get(id) {
    return apiRequest(`/students/${id}`);
  },

  async create(studentData, imageFile = null) {
    // DIRECT fetch — bypasses apiRequest wrapper to guarantee correct multipart/form-data
    const token = getToken();
    const formData = new FormData();

    // Append required fields
    formData.append('roll_number', studentData.roll_number || '');
    formData.append('name', studentData.name || '');
    formData.append('class_name', studentData.class_name || '');

    // Append optional fields
    if (studentData.year) formData.append('year', studentData.year);
    if (studentData.department) formData.append('department', studentData.department);
    if (studentData.email) formData.append('email', studentData.email);
    if (studentData.phone) formData.append('phone', studentData.phone);

    // Append image file if provided
    if (imageFile) {
      formData.append('image', imageFile);
    }

    // Debug: log exactly what we are sending
    console.log('StudentAPI.create — sending FormData:');
    for (const [key, value] of formData.entries()) {
      console.log(`  ${key}:`, value instanceof File ? `[File: ${value.name}]` : value);
    }

    // IMPORTANT: Do NOT set Content-Type header — browser must set it with boundary
    const response = await fetch(`${API_BASE}/students`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      console.error('StudentAPI.create — error response:', error);
      const errorMsg = error.message || error.detail || `Request failed (${response.status})`;
      throw new Error(errorMsg);
    }

    return await response.json();
  },

  async update(id, data) {
    return apiRequest(`/students/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async delete(id) {
    return apiRequest(`/students/${id}`, { method: 'DELETE' });
  },

  async uploadImages(studentId, files) {
    const formData = new FormData();
    files.forEach(file => formData.append('images', file));
    return apiRequest(`/students/${studentId}/images`, {
      method: 'POST',
      body: formData,
    });
  },

  async deleteImage(studentId, imageId) {
    return apiRequest(`/students/${studentId}/images/${imageId}`, {
      method: 'DELETE',
    });
  },

  async hardDeleteInactive() {
    return apiRequest('/students/cleanup/all', { method: 'DELETE' });
  },
};


// ─── Attendance Endpoints ───────────────────────────────────────
const AttendanceAPI = {
  async list(page = 1, limit = 50, filters = {}) {
    const params = new URLSearchParams({ page, limit });
    if (filters.startDate)  params.append('start_date', filters.startDate);
    if (filters.endDate)    params.append('end_date',   filters.endDate);
    if (filters.subject)    params.append('subject',    filters.subject);
    if (filters.studentId)  params.append('student_id', filters.studentId);
    if (filters.class_name) params.append('class_name', filters.class_name);
    if (filters.year)       params.append('year',       filters.year);
    return apiRequest(`/attendance?${params}`);
  },

  // Returns array of distinct class_name strings from DB
  async getClasses() {
    return apiRequest('/attendance/classes');
  },

  async getTrend() {
    return apiRequest(`/attendance/trend`);
  },

  async getSummary() {
    return apiRequest(`/attendance/summary`);
  },


  async processGroup(imageFile, subject, date = null, className = null) {
    const token = getToken();
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('subject', subject);
    if (date)      formData.append('date',       date);
    if (className) formData.append('class_name', className);

    const response = await fetch(`${API_BASE}/attendance/process-group`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const errorMsg = error.message || error.detail || `Request failed (${response.status})`;
      throw new Error(errorMsg);
    }

    return await response.json();
  },

  async createManual(data) {
    return apiRequest('/attendance/manual', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Full update — sends all editable fields
  async update(id, data) {
    return apiRequest(`/attendance/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async delete(id) {
    return apiRequest(`/attendance/${id}`, { method: 'DELETE' });
  },

  async export(filters = {}) {
    const params = new URLSearchParams();
    if (filters.startDate)  params.append('start_date', filters.startDate);
    if (filters.endDate)    params.append('end_date',   filters.endDate);
    if (filters.subject)    params.append('subject',    filters.subject);
    if (filters.class_name) params.append('class_name', filters.class_name);
    params.append('format', filters.format || 'xlsx');
    return apiRequest(`/attendance/export?${params}`);
  },
};


// ─── Task Endpoints ─────────────────────────────────────────────
const TaskAPI = {
  async getStatus(taskId) {
    return apiRequest(`/tasks/${taskId}/status`);
  },

  async pollUntilDone(taskId, onUpdate, interval = 2000) {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const task = await this.getStatus(taskId);
          if (onUpdate) onUpdate(task);

          if (task.status === 'completed') {
            resolve(task);
          } else if (task.status === 'failed') {
            reject(new Error(task.error_message || 'Task failed'));
          } else {
            setTimeout(poll, interval);
          }
        } catch (err) {
          reject(err);
        }
      };
      poll();
    });
  },
};
