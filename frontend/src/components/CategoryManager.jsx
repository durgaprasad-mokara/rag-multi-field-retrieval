import React, { useState } from "react";
import {
  Folder,
  FolderPlus,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  ChevronRight,
  ChevronDown,
  Layers,
} from "lucide-react";
import {
  createCategory,
  updateCategory,
  deleteCategory,
  createDocumentType,
  updateDocumentType,
  deleteDocumentType,
} from "../services/api";

export default function CategoryManager({
  categories,
  onCategoriesUpdated,
  onClose,
  onError,
}) {
  const [expandedCatId, setExpandedCatId] = useState(categories[0]?.id ?? null);
  const [newCatName, setNewCatName] = useState("");
  const [newCatDesc, setNewCatDesc] = useState("");
  const [isAddingCat, setIsAddingCat] = useState(false);

  const [editingCatId, setEditingCatId] = useState(null);
  const [editCatName, setEditCatName] = useState("");
  const [editCatDesc, setEditCatDesc] = useState("");

  const [addingTypeId, setAddingTypeId] = useState(null);
  const [newTypeName, setNewTypeName] = useState("");
  const [newTypeDesc, setNewTypeDesc] = useState("");

  const [editingTypeId, setEditingTypeId] = useState(null);
  const [editTypeName, setEditTypeName] = useState("");
  const [editTypeDesc, setEditTypeDesc] = useState("");

  // ── Category Actions ──────────────────────────────────────────

  async function handleAddCategory(e) {
    e.preventDefault();
    if (!newCatName.trim()) return;
    try {
      await createCategory({
        name: newCatName.trim(),
        description: newCatDesc.trim() || null,
      });
      setNewCatName("");
      setNewCatDesc("");
      setIsAddingCat(false);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to create category");
    }
  }

  async function handleSaveCategory(id) {
    if (!editCatName.trim()) return;
    try {
      await updateCategory(id, {
        name: editCatName.trim(),
        description: editCatDesc.trim() || null,
      });
      setEditingCatId(null);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to update category");
    }
  }

  async function handleDeleteCategory(id, name) {
    if (
      !window.confirm(
        `Are you sure you want to delete category "${name}"? All nested types and documents will be deleted.`
      )
    ) {
      return;
    }
    try {
      await deleteCategory(id);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to delete category");
    }
  }

  // ── Type Actions ──────────────────────────────────────────────

  async function handleAddType(catId, e) {
    e.preventDefault();
    if (!newTypeName.trim()) return;
    try {
      await createDocumentType(catId, {
        name: newTypeName.trim(),
        description: newTypeDesc.trim() || null,
      });
      setNewTypeName("");
      setNewTypeDesc("");
      setAddingTypeId(null);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to add document type");
    }
  }

  async function handleSaveType(typeId) {
    if (!editTypeName.trim()) return;
    try {
      await updateDocumentType(typeId, {
        name: editTypeName.trim(),
        description: editTypeDesc.trim() || null,
      });
      setEditingTypeId(null);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to update document type");
    }
  }

  async function handleDeleteType(typeId, name) {
    if (
      !window.confirm(
        `Are you sure you want to delete type "${name}"? All associated documents will be deleted.`
      )
    ) {
      return;
    }
    try {
      await deleteDocumentType(typeId);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to delete document type");
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="modal-icon-badge">
              <Layers size={20} />
            </div>
            <div>
              <h3>Category &amp; Type Management</h3>
              <p className="modal-subtitle">
                Organize documents into custom industries, domains, and types
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Add Category Trigger / Form */}
          {!isAddingCat ? (
            <button
              className="btn btn-primary btn-sm"
              style={{ marginBottom: "16px" }}
              onClick={() => setIsAddingCat(true)}
            >
              <FolderPlus size={16} /> Add New Category
            </button>
          ) : (
            <form onSubmit={handleAddCategory} className="form-card">
              <div className="form-row">
                <input
                  type="text"
                  placeholder="Category Name (e.g. Finance, Legal, HR)"
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  className="input-text"
                  autoFocus
                  required
                />
                <input
                  type="text"
                  placeholder="Optional Description"
                  value={newCatDesc}
                  onChange={(e) => setNewCatDesc(e.target.value)}
                  className="input-text"
                />
              </div>
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  justifyContent: "flex-end",
                  marginTop: "8px",
                }}
              >
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setIsAddingCat(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary btn-sm">
                  Save Category
                </button>
              </div>
            </form>
          )}

          {/* Categories List */}
          <div className="category-manager-list">
            {categories.map((cat) => {
              const isExpanded = expandedCatId === cat.id;
              const isEditing = editingCatId === cat.id;

              return (
                <div key={cat.id} className="category-manager-item">
                  {/* Category Row Header */}
                  <div className="category-row-header">
                    <button
                      className="category-expand-btn"
                      onClick={() =>
                        setExpandedCatId(isExpanded ? null : cat.id)
                      }
                    >
                      {isExpanded ? (
                        <ChevronDown size={16} />
                      ) : (
                        <ChevronRight size={16} />
                      )}
                      <Folder size={16} className="category-icon" />
                    </button>

                    {isEditing ? (
                      <div className="inline-edit-row">
                        <input
                          type="text"
                          value={editCatName}
                          onChange={(e) => setEditCatName(e.target.value)}
                          className="input-text-sm"
                          autoFocus
                        />
                        <button
                          className="btn-icon text-success"
                          onClick={() => handleSaveCategory(cat.id)}
                          title="Save"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          className="btn-icon"
                          onClick={() => setEditingCatId(null)}
                          title="Cancel"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ) : (
                      <div className="category-info-meta">
                        <span className="category-title-text">{cat.name}</span>
                        <span className="badge-count">
                          {cat.types?.length || 0} types
                        </span>
                        {cat.document_count > 0 && (
                          <span className="badge-count-doc">
                            {cat.document_count} doc
                            {cat.document_count !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    )}

                    <div className="row-actions">
                      {!isEditing && (
                        <>
                          <button
                            className="btn-icon"
                            onClick={() => {
                              setEditingCatId(cat.id);
                              setEditCatName(cat.name);
                              setEditCatDesc(cat.description || "");
                            }}
                            title="Edit Category"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            className="btn-icon text-danger"
                            onClick={() =>
                              handleDeleteCategory(cat.id, cat.name)
                            }
                            title="Delete Category"
                          >
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Types sub-list */}
                  {isExpanded && (
                    <div className="types-sublist">
                      {cat.types && cat.types.length > 0 ? (
                        cat.types.map((type) => {
                          const isEditingType = editingTypeId === type.id;

                          return (
                            <div key={type.id} className="type-row-item">
                              {isEditingType ? (
                                <div className="inline-edit-row">
                                  <input
                                    type="text"
                                    value={editTypeName}
                                    onChange={(e) =>
                                      setEditTypeName(e.target.value)
                                    }
                                    className="input-text-sm"
                                    autoFocus
                                  />
                                  <button
                                    className="btn-icon text-success"
                                    onClick={() => handleSaveType(type.id)}
                                    title="Save"
                                  >
                                    <Check size={14} />
                                  </button>
                                  <button
                                    className="btn-icon"
                                    onClick={() => setEditingTypeId(null)}
                                    title="Cancel"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              ) : (
                                <>
                                  <span className="type-title-text">
                                    • {type.name}
                                  </span>
                                  {type.document_count > 0 && (
                                    <span className="badge-count-doc-sm">
                                      {type.document_count} doc
                                      {type.document_count !== 1 ? "s" : ""}
                                    </span>
                                  )}
                                  <div className="row-actions-sm">
                                    <button
                                      className="btn-icon"
                                      onClick={() => {
                                        setEditingTypeId(type.id);
                                        setEditTypeName(type.name);
                                        setEditTypeDesc(type.description || "");
                                      }}
                                      title="Edit Type"
                                    >
                                      <Edit2 size={12} />
                                    </button>
                                    <button
                                      className="btn-icon text-danger"
                                      onClick={() =>
                                        handleDeleteType(type.id, type.name)
                                      }
                                      title="Delete Type"
                                    >
                                      <Trash2 size={12} />
                                    </button>
                                  </div>
                                </>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <p className="empty-types-hint">
                          No document types added yet.
                        </p>
                      )}

                      {/* Add Type Form / Trigger */}
                      {addingTypeId === cat.id ? (
                        <form
                          onSubmit={(e) => handleAddType(cat.id, e)}
                          className="form-add-type"
                        >
                          <input
                            type="text"
                            placeholder="New Type Name (e.g. Study Materials, Policies)"
                            value={newTypeName}
                            onChange={(e) => setNewTypeName(e.target.value)}
                            className="input-text-sm"
                            autoFocus
                            required
                          />
                          <div
                            style={{
                              display: "flex",
                              gap: "6px",
                              justifyContent: "flex-end",
                              marginTop: "6px",
                            }}
                          >
                            <button
                              type="button"
                              className="btn btn-secondary btn-xs"
                              onClick={() => setAddingTypeId(null)}
                            >
                              Cancel
                            </button>
                            <button
                              type="submit"
                              className="btn btn-primary btn-xs"
                            >
                              Add Type
                            </button>
                          </div>
                        </form>
                      ) : (
                        <button
                          className="btn-add-type-trigger"
                          onClick={() => {
                            setAddingTypeId(cat.id);
                            setNewTypeName("");
                            setNewTypeDesc("");
                          }}
                        >
                          <Plus size={12} /> Add type under {cat.name}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
