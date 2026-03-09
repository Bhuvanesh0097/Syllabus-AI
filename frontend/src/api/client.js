/**
 * API Client — centralized HTTP communication with the backend.
 */

const API_BASE = 'http://localhost:8000';

class ApiClient {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error.message === 'Failed to fetch') {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      throw error;
    }
  }

  // ── Subjects ────────────────────────────────────────────
  async getSubjects() {
    return this.request('/api/subjects/');
  }

  async getSubject(code) {
    return this.request(`/api/subjects/${code}`);
  }

  async getUnit(subjectCode, unitNumber) {
    return this.request(`/api/subjects/${subjectCode}/units/${unitNumber}`);
  }

  async getSubjectStats(subjectCode) {
    return this.request(`/api/subjects/${subjectCode}/stats`);
  }

  // ── Chat ────────────────────────────────────────────────
  async startSession(studentInfo) {
    return this.request('/api/chat/start-session', {
      method: 'POST',
      body: JSON.stringify({
        student_name: studentInfo.name,
        subject_code: studentInfo.subject || studentInfo.subjectCode,
        unit_number: studentInfo.unit || studentInfo.unitNumber,
        section: studentInfo.section,
        department: studentInfo.department || 'CSE',
        year: studentInfo.year || '2nd Year',
        semester: studentInfo.semester || '4th Semester',
      }),
    });
  }

  async sendMessage(message, options = {}) {
    return this.request('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({
        message,
        subject_code: options.subjectCode,
        unit_number: options.unitNumber,
        section: options.section,
        answer_style: options.answerStyle,
        chat_id: options.chatId,
        tone: options.tone,
      }),
    });
  }

  async getChatSessions() {
    return this.request('/api/chat/sessions');
  }

  async getChatSession(chatId) {
    return this.request(`/api/chat/sessions/${chatId}`);
  }

  async deleteChatSession(chatId) {
    return this.request(`/api/chat/sessions/${chatId}`, {
      method: 'DELETE',
    });
  }

  async createNewChat(subjectCode, title) {
    return this.request(`/api/chat/sessions/new?subject_code=${subjectCode || ''}&title=${title || ''}`, {
      method: 'POST',
    });
  }

  // ── Documents ───────────────────────────────────────────
  async uploadDocument(file, subjectCode, unitNumber, section) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject_code', subjectCode);
    formData.append('unit_number', unitNumber);
    if (section) formData.append('section', section);

    return this.request('/api/documents/upload', {
      method: 'POST',
      headers: {}, // Let browser set content-type for FormData
      body: formData,
    });
  }

  async getDocuments(subjectCode, section) {
    const params = section ? `?section=${section}` : '';
    return this.request(`/api/documents/${subjectCode}${params}`);
  }

  async getDocumentStats(subjectCode, section) {
    const params = section ? `?section=${section}` : '';
    return this.request(`/api/documents/${subjectCode}/stats${params}`);
  }

  async deleteDocument(subjectCode, filename, section) {
    const params = section ? `?section=${section}` : '';
    return this.request(`/api/documents/${subjectCode}/${encodeURIComponent(filename)}${params}`, {
      method: 'DELETE',
    });
  }

  async getSectionOverview(subjectCode) {
    return this.request(`/api/documents/${subjectCode}/sections`);
  }

  // ── Study Plan ──────────────────────────────────────────
  async generateStudyPlan(options) {
    return this.request('/api/study-plan/generate', {
      method: 'POST',
      body: JSON.stringify(options),
    });
  }

  // ── Memory ──────────────────────────────────────────────
  async getProgress() {
    return this.request('/api/memory/progress');
  }

  async getSubjectProgress(subjectCode) {
    return this.request(`/api/memory/progress/${subjectCode}`);
  }

  async saveProfile(profileData) {
    return this.request('/api/memory/profile', {
      method: 'POST',
      body: JSON.stringify(profileData),
    });
  }

  async getProfile() {
    return this.request('/api/memory/profile');
  }

  async getWelcomeBack() {
    return this.request('/api/memory/welcome-back');
  }

  async getWelcomeBackByName(name) {
    return this.request(`/api/memory/welcome-back/${encodeURIComponent(name)}`);
  }

  // ── Study Mode ─────────────────────────────────────────────
  async getStudyQuestions(subjectCode, unitNumber, mode, section) {
    return this.request('/api/study-mode/questions', {
      method: 'POST',
      body: JSON.stringify({
        subject_code: subjectCode,
        unit_number: unitNumber,
        mode: mode,
        section: section || null,
      }),
    });
  }

  async getQuestionAnswer(subjectCode, unitNumber, mode, question, section) {
    return this.request('/api/study-mode/answer', {
      method: 'POST',
      body: JSON.stringify({
        subject_code: subjectCode,
        unit_number: unitNumber,
        mode: mode,
        question: question,
        section: section || null,
      }),
    });
  }

  // ── Admin ────────────────────────────────────────────────
  async verifyAdminPin(pin) {
    return this.request('/api/admin/verify-pin', {
      method: 'POST',
      body: JSON.stringify({ pin }),
    });
  }

  // ── Health ──────────────────────────────────────────────
  async healthCheck() {
    return this.request('/health');
  }

  async getStatus() {
    return this.request('/api/status');
  }
}

export const api = new ApiClient();
export default api;
