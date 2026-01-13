'use client';

import { useState, useEffect } from 'react';

interface ConfigEditorProps {
  configName: string;
  onClose: () => void;
}

export default function ConfigEditor({ configName, onClose }: ConfigEditorProps) {
  const [content, setContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configType, setConfigType] = useState<string>('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

  useEffect(() => {
    fetchConfig();
  }, [configName]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_URL}/api/config/${configName}`);
      if (!response.ok) {
        throw new Error('Failed to load config');
      }
      const data = await response.json();
      
      if (data.type === 'text') {
        setContent(data.content);
        setOriginalContent(data.content);
      } else if (data.raw) {
        setContent(data.raw);
        setOriginalContent(data.raw);
      } else if (data.type === 'json') {
        setContent(JSON.stringify(data.content, null, 2));
        setOriginalContent(JSON.stringify(data.content, null, 2));
      } else {
        setContent(data.content);
        setOriginalContent(data.content);
      }
      setConfigType(data.type);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      let payload: any = {};
      
      if (configType === 'text') {
        payload.content = content;
      } else if (configType === 'json') {
        try {
          payload.content = JSON.parse(content);
        } catch (e) {
          throw new Error('Invalid JSON format');
        }
      } else if (configType === 'yaml' || configType === 'yml' || configType === 'toml') {
        payload.content = content;
      } else {
        payload.content = content;
      }
      
      const response = await fetch(`${API_URL}/api/config/${configName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save config');
      }
      
      setOriginalContent(content);
      alert('Config saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveField = async (fieldPath: string, value: string) => {
    try {
      setSaving(true);
      setError(null);
      
      const response = await fetch(`${API_URL}/api/config/${configName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: value,
          field_path: fieldPath,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save field');
      }
      
      await fetchConfig();
      alert('Field saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save field');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}>
        <div style={{ color: '#fff' }}>Loading...</div>
      </div>
    );
  }

  const isDirty = content !== originalContent;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '2rem',
    }}>
      <div style={{
        backgroundColor: '#1e1e1e',
        borderRadius: '8px',
        width: '100%',
        maxWidth: '900px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
      }}>
        <div style={{
          padding: '1.5rem',
          borderBottom: '1px solid #333',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <h2 style={{ margin: 0, color: '#fff', fontSize: '1.5rem' }}>
            Edit {configName}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#fff',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.5rem',
            }}
          >
            ×
          </button>
        </div>
        
        {configName === 'settings.yml' && (
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid #333',
            backgroundColor: '#252525',
          }}>
            <div style={{ marginBottom: '0.5rem', color: '#fff', fontWeight: 'bold' }}>
              Quick Edit: infoForwarding.secret
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                id="forwarding-secret-input"
                placeholder="Enter forwarding secret"
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  backgroundColor: '#333',
                  border: '1px solid #555',
                  borderRadius: '4px',
                  color: '#fff',
                }}
              />
              <button
                onClick={() => {
                  const input = document.getElementById('forwarding-secret-input') as HTMLInputElement;
                  if (input?.value) {
                    handleSaveField('infoForwarding.secret', input.value);
                  }
                }}
                disabled={saving}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#4CAF50',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                Save Secret
              </button>
            </div>
          </div>
        )}
        
        {configName === 'resources.json' && (
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid #333',
            backgroundColor: '#252525',
          }}>
            <div style={{ marginBottom: '0.5rem', color: '#fff', fontWeight: 'bold' }}>
              Quick Edit: velocity-secret
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                id="velocity-secret-input"
                placeholder="Enter velocity secret"
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  backgroundColor: '#333',
                  border: '1px solid #555',
                  borderRadius: '4px',
                  color: '#fff',
                }}
              />
              <button
                onClick={() => {
                  const input = document.getElementById('velocity-secret-input') as HTMLInputElement;
                  if (input?.value) {
                    handleSaveField('velocity-secret', input.value);
                  }
                }}
                disabled={saving}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#4CAF50',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                Save Secret
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            padding: '1rem 1.5rem',
            backgroundColor: '#ff4444',
            color: '#fff',
            borderBottom: '1px solid #333',
          }}>
            {error}
          </div>
        )}

        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '1.5rem',
        }}>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{
              width: '100%',
              height: '100%',
              minHeight: '400px',
              backgroundColor: '#1e1e1e',
              color: '#d4d4d4',
              border: '1px solid #333',
              borderRadius: '4px',
              padding: '1rem',
              fontFamily: 'monospace',
              fontSize: '14px',
              resize: 'vertical',
            }}
            spellCheck={false}
          />
        </div>

        <div style={{
          padding: '1.5rem',
          borderTop: '1px solid #333',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '1rem',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#555',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !isDirty}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: isDirty ? '#4CAF50' : '#555',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: (saving || !isDirty) ? 'not-allowed' : 'pointer',
              opacity: (saving || !isDirty) ? 0.6 : 1,
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

