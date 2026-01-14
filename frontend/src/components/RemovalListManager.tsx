import { useState, useCallback, useEffect } from 'react';
import {
  getRemovalLists,
  getActiveRemovalLists,
  uploadRemovalList,
  updateRemovalListStatus,
  deleteRemovalList,
  type RemovalList,
  type ActiveRemovalLists
} from '../services/api';
import './RemovalListManager.css';

interface RemovalListManagerProps {
  showUpload?: boolean;
  onListsChange?: () => void;
}

export default function RemovalListManager({ showUpload = true, onListsChange }: RemovalListManagerProps) {
  const [accountLists, setAccountLists] = useState<RemovalList[]>([]);
  const [contactLists, setContactLists] = useState<RemovalList[]>([]);
  const [activeLists, setActiveLists] = useState<ActiveRemovalLists>({ accountRemovalList: null, contactRemovalList: null });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadType, setUploadType] = useState<'account' | 'contact' | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadLists = useCallback(async () => {
    try {
      setLoading(true);
      const [accountData, contactData, activeData] = await Promise.all([
        getRemovalLists('account'),
        getRemovalLists('contact'),
        getActiveRemovalLists()
      ]);
      setAccountLists(accountData);
      setContactLists(contactData);
      setActiveLists(activeData);
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to load removal lists:', error);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  const handleFileUpload = useCallback(async (file: File, listType: 'account' | 'contact') => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please select a CSV file');
      return;
    }

    setIsUploading(true);
    try {
      await uploadRemovalList(file, listType);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to upload removal list:', error);
      }
      alert('Failed to upload removal list');
    } finally {
      setIsUploading(false);
      setUploadType(null);
    }
  }, [loadLists, onListsChange]);

  const handleDragOver = useCallback((e: React.DragEvent, type: 'account' | 'contact') => {
    e.preventDefault();
    setIsDragging(true);
    setUploadType(type);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setUploadType(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, type: 'account' | 'contact') => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.name.toLowerCase().endsWith('.csv')
    );

    if (files.length > 0) {
      handleFileUpload(files[0], type);
    } else {
      alert('Please drop a CSV file');
    }
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'account' | 'contact') => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFileUpload(files[0], type);
      e.target.value = '';
    }
  }, [handleFileUpload]);

  const handleToggleActive = useCallback(async (listId: string, currentlyActive: boolean) => {
    try {
      await updateRemovalListStatus(listId, !currentlyActive);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to update removal list status:', error);
      }
      alert('Failed to update removal list status');
    }
  }, [loadLists, onListsChange]);

  const handleDelete = useCallback(async (listId: string) => {
    if (!confirm('Are you sure you want to delete this removal list?')) {
      return;
    }

    try {
      await deleteRemovalList(listId);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to delete removal list:', error);
      }
      alert('Failed to delete removal list');
    }
  }, [loadLists, onListsChange]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderListSection = (
    title: string,
    type: 'account' | 'contact',
    lists: RemovalList[],
    activeList: RemovalList | null
  ) => (
    <div className="removal-list-section">
      <h3>{title}</h3>

      {showUpload && (
        <div
          className={`removal-upload-area ${isDragging && uploadType === type ? 'dragging' : ''}`}
          onDragOver={(e) => handleDragOver(e, type)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, type)}
        >
          <input
            type="file"
            id={`removal-${type}-input`}
            accept=".csv"
            onChange={(e) => handleFileInput(e, type)}
            className="removal-file-input"
            disabled={isUploading}
          />
          <label htmlFor={`removal-${type}-input`} className="removal-upload-label">
            {isUploading && uploadType === type ? (
              <span className="uploading-text">Uploading...</span>
            ) : (
              <>
                <span className="upload-icon-small">+</span>
                <span>Upload new {type} removal list (CSV)</span>
              </>
            )}
          </label>
        </div>
      )}

      {activeList ? (
        <div className="active-list-card">
          <div className="active-badge">Active</div>
          <div className="list-info">
            <span className="list-name">{activeList.originalName}</span>
            <span className="list-meta">
              {activeList.entryCount.toLocaleString()} {type === 'account' ? 'accounts' : 'contacts'}
              {' | '}
              Uploaded {formatDate(activeList.uploadedAt)}
            </span>
          </div>
          {!activeList.fileExists && (
            <span className="file-missing-warning" title="File is no longer available">Missing</span>
          )}
        </div>
      ) : (
        <div className="no-active-list">
          <span className="no-list-text">No active {type} removal list</span>
        </div>
      )}

      {lists.length > 0 && (
        <div className="list-history">
          <h4>History ({lists.length})</h4>
          <div className="list-items">
            {lists.map(list => (
              <div key={list.id} className={`list-item ${list.isActive ? 'active' : ''}`}>
                <div className="list-item-info">
                  <span className="list-item-name">{list.originalName}</span>
                  <span className="list-item-meta">
                    {list.entryCount.toLocaleString()} entries | {formatFileSize(list.fileSize)}
                    {' | '}{formatDate(list.uploadedAt)}
                  </span>
                </div>
                <div className="list-item-actions">
                  {list.fileExists ? (
                    <button
                      className={`toggle-active-btn ${list.isActive ? 'active' : ''}`}
                      onClick={() => handleToggleActive(list.id, list.isActive)}
                      title={list.isActive ? 'Deactivate' : 'Activate'}
                    >
                      {list.isActive ? 'Active' : 'Activate'}
                    </button>
                  ) : (
                    <span className="file-missing">File missing</span>
                  )}
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(list.id)}
                    title="Delete"
                  >
                    x
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return <div className="removal-list-manager loading">Loading removal lists...</div>;
  }

  return (
    <div className="removal-list-manager">
      {renderListSection(
        'Account Removal List',
        'account',
        accountLists,
        activeLists.accountRemovalList
      )}
      {renderListSection(
        'Contact Removal List',
        'contact',
        contactLists,
        activeLists.contactRemovalList
      )}
    </div>
  );
}
