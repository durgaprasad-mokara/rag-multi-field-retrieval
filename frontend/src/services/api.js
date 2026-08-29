import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 120000, // 2 min timeout for large uploads / LLM calls
});

/**
 * Upload a document file to the backend.
 * @param {File} file
 * @param {function} onProgress - optional progress callback (0-100)
 */
export async function uploadDocument(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

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

/**
 * Fetch all uploaded documents.
 */
export async function getDocuments() {
  const response = await api.get("/documents");
  return response.data;
}

/**
 * Delete a document by ID.
 * @param {number} id
 */
export async function deleteDocument(id) {
  const response = await api.delete(`/documents/${id}`);
  return response.data;
}

/**
 * Send a chat message and get a RAG-powered response.
 * @param {string} question
 * @param {number|null} documentId - optional document filter
 */
export async function sendMessage(question, documentId = null) {
  const payload = { question };
  if (documentId !== null) {
    payload.document_id = documentId;
  }
  const response = await api.post("/chat", payload);
  return response.data;
}

/**
 * Fetch chat message history from PostgreSQL.
 * @param {number|null} documentId - optional document filter
 */
export async function getChatHistory(documentId = null) {
  const params = documentId ? { document_id: documentId } : {};
  const response = await api.get("/chat/history", { params });
  return response.data;
}

/**
 * Clear all chat history in PostgreSQL.
 */
export async function clearChatHistory() {
  const response = await api.delete("/chat/history");
  return response.data;
}

