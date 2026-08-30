import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 120000, // 2 min timeout for large uploads / LLM calls
});

// ── Categories & Types ────────────────────────────────────────

export async function getCategories() {
  const response = await api.get("/categories");
  return response.data;
}

export async function createCategory(data) {
  const response = await api.post("/categories", data);
  return response.data;
}

export async function updateCategory(id, data) {
  const response = await api.put(`/categories/${id}`, data);
  return response.data;
}

export async function deleteCategory(id) {
  const response = await api.delete(`/categories/${id}`);
  return response.data;
}

export async function createDocumentType(categoryId, data) {
  const response = await api.post(`/categories/${categoryId}/types`, data);
  return response.data;
}

export async function updateDocumentType(typeId, data) {
  const response = await api.put(`/categories/types/${typeId}`, data);
  return response.data;
}

export async function deleteDocumentType(typeId) {
  const response = await api.delete(`/categories/types/${typeId}`);
  return response.data;
}

// ── Document Management ───────────────────────────────────────

export async function uploadDocument(file, categoryId, typeId, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category_id", categoryId);
  formData.append("type_id", typeId);

  const response = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return response.data;
}

export async function getDocuments(categoryId = null, typeId = null) {
  const params = {};
  if (categoryId) params.category_id = categoryId;
  if (typeId) params.type_id = typeId;
  const response = await api.get("/documents", { params });
  return response.data;
}

export async function getDocument(id) {
  const response = await api.get(`/documents/${id}`);
  return response.data;
}

export async function deleteDocument(id) {
  const response = await api.delete(`/documents/${id}`);
  return response.data;
}

// ── Chat Sessions & Document-Specific RAG ─────────────────────

export async function createChatSession(documentId, documentIds = null, title = null) {
  const payload = {};
  if (documentIds && documentIds.length > 0) {
    payload.document_ids = documentIds;
    payload.document_id = documentIds[0];
  } else if (documentId) {
    payload.document_id = documentId;
  }
  if (title) payload.title = title;
  const response = await api.post("/chat/sessions", payload);
  return response.data;
}

export async function getChatSessions(documentId = null) {
  const params = documentId ? { document_id: documentId } : {};
  const response = await api.get("/chat/sessions", { params });
  return response.data;
}

export async function getChatSession(sessionId) {
  const response = await api.get(`/chat/sessions/${sessionId}`);
  return response.data;
}

export async function deleteChatSession(sessionId) {
  const response = await api.delete(`/chat/sessions/${sessionId}`);
  return response.data;
}

export async function sendMessage(question, sessionId = null, documentId = null, documentIds = null) {
  const payload = { question };
  if (sessionId) payload.session_id = sessionId;
  if (documentIds && documentIds.length > 0) payload.document_ids = documentIds;
  else if (documentId) payload.document_id = documentId;
  const response = await api.post("/chat", payload);
  return response.data;
}

export async function getChatHistory(sessionId = null, documentId = null) {
  const params = {};
  if (sessionId) params.session_id = sessionId;
  else if (documentId) params.document_id = documentId;
  const response = await api.get("/chat/history", { params });
  return response.data;
}

export async function clearChatHistory(sessionId = null, documentId = null) {
  const params = {};
  if (sessionId) params.session_id = sessionId;
  else if (documentId) params.document_id = documentId;
  const response = await api.delete("/chat/history", { params });
  return response.data;
}
