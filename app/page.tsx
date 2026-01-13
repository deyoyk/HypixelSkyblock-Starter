'use client'

import { useState, useEffect } from 'react'
import LogViewer from './components/LogViewer'

interface Instance {
  id: string
  instance: number
  running: boolean
}

interface GameServer {
  name: string
  instances: Instance[]
}

interface ServerData {
  proxy: { id: string; name: string; type: string; running: boolean }
  limbo: { id: string; name: string; type: string; running: boolean }
  services: Array<{ id: string; name: string; type: string; running: boolean }>
  gameservers: { [key: string]: GameServer }
}

interface DownloadStatus {
  status: string
  progress: number
  current: string
  errors: string[]
}

export default function Home() {
  const [data, setData] = useState<ServerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [logViewer, setLogViewer] = useState<{ serverId: string; serverName: string } | null>(null)
  const [selectedServices, setSelectedServices] = useState<Set<string>>(new Set())
  const [downloadStatus, setDownloadStatus] = useState<DownloadStatus>({ status: 'idle', progress: 0, current: '', errors: [] })

  const fetchServers = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/servers')
      const serverData = await response.json()
      setData(serverData)
    } catch (error) {
      console.error('Error fetching servers:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchServers()
    const interval = setInterval(fetchServers, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const fetchDownloadStatus = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/download/status')
        const status = await response.json()
        setDownloadStatus(status)
      } catch (error) {
        console.error('Error fetching download status:', error)
      }
    }
    
    fetchDownloadStatus()
    const interval = setInterval(fetchDownloadStatus, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleDownload = async (force: boolean = false) => {
    try {
      const response = await fetch('http://localhost:5000/api/download/all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force })
      })
      const result = await response.json()
      if (!response.ok) {
        alert(result.error || 'Failed to start download')
      }
    } catch (error) {
      alert('Error starting download')
    }
  }

  const handleDownloadSelected = async (force: boolean = false) => {
    if (selectedServices.size === 0) {
      alert('Please select at least one service to download')
      return
    }
    
    try {
      const response = await fetch('http://localhost:5000/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force, selected: Array.from(selectedServices) })
      })
      const result = await response.json()
      if (!response.ok) {
        alert(result.error || 'Failed to start download')
      }
    } catch (error) {
      alert('Error starting download')
    }
  }

  const toggleServiceSelection = (serviceId: string) => {
    const newSelected = new Set(selectedServices)
    if (newSelected.has(serviceId)) {
      newSelected.delete(serviceId)
    } else {
      newSelected.add(serviceId)
    }
    setSelectedServices(newSelected)
  }

  const handleStart = async (serverId: string) => {
    setActionLoading(serverId)
    try {
      const response = await fetch(`http://localhost:5000/api/servers/${serverId}/start`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok) {
        setTimeout(fetchServers, 500)
      } else {
        alert(result.error || 'Failed to start server')
      }
    } catch (error) {
      alert('Error starting server')
    } finally {
      setActionLoading(null)
    }
  }

  const handleStop = async (serverId: string) => {
    setActionLoading(serverId)
    try {
      const response = await fetch(`http://localhost:5000/api/servers/${serverId}/stop`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok) {
        setTimeout(fetchServers, 500)
      } else {
        alert(result.error || 'Failed to stop server')
      }
    } catch (error) {
      alert('Error stopping server')
    } finally {
      setActionLoading(null)
    }
  }

  const addInstance = async (serverName: string) => {
    if (!data) return
    const server = data.gameservers[serverName]
    if (!server) return
    
    const maxInstance = Math.max(...server.instances.map(i => i.instance), -1)
    const newInstanceId = `${serverName.toLowerCase()}_${maxInstance + 1}`
    
    setActionLoading(newInstanceId)
    try {
      const response = await fetch(`http://localhost:5000/api/servers/${newInstanceId}/start`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok) {
        setTimeout(fetchServers, 500)
      } else {
        alert(result.error || 'Failed to start instance')
      }
    } catch (error) {
      alert('Error starting instance')
    } finally {
      setActionLoading(null)
    }
  }

  const removeInstance = async (serverName: string, instanceNum: number) => {
    const instanceId = `${serverName.toLowerCase()}_${instanceNum}`
    setActionLoading(instanceId)
    try {
      const response = await fetch(`http://localhost:5000/api/servers/${instanceId}/remove`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok) {
        setTimeout(fetchServers, 500)
      } else {
        alert(result.error || 'Failed to remove instance')
      }
    } catch (error) {
      alert('Error removing instance')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading || !data) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Loading servers...</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto', backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ marginBottom: '2rem', backgroundColor: '#fff', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '2rem', color: '#333' }}>Server Manager</h1>
            <p style={{ margin: '0.5rem 0 0 0', color: '#666', fontSize: '0.875rem' }}>Manage and monitor your game servers</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => handleDownload(false)}
              disabled={downloadStatus.status === 'downloading'}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: downloadStatus.status === 'downloading' ? 'not-allowed' : 'pointer',
                opacity: downloadStatus.status === 'downloading' ? 0.6 : 1,
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              Download All
            </button>
            <button
              onClick={() => handleDownload(true)}
              disabled={downloadStatus.status === 'downloading'}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#ff9800',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: downloadStatus.status === 'downloading' ? 'not-allowed' : 'pointer',
                opacity: downloadStatus.status === 'downloading' ? 0.6 : 1,
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              Redownload All
            </button>
          </div>
        </div>
        {downloadStatus.status === 'downloading' && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: '#1976d2', fontWeight: '500' }}>
                Downloading: {downloadStatus.current || 'Preparing...'}
              </span>
              <span style={{ fontSize: '0.875rem', color: '#1976d2', fontWeight: '500' }}>
                {downloadStatus.progress}%
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', backgroundColor: '#bbdefb', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${downloadStatus.progress}%`,
                  height: '100%',
                  backgroundColor: '#2196f3',
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
          </div>
        )}
        {downloadStatus.status === 'completed' && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#e8f5e9', borderRadius: '4px', color: '#2e7d32', fontSize: '0.875rem' }}>
            Download completed successfully!
          </div>
        )}
        {downloadStatus.errors.length > 0 && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#ffebee', borderRadius: '4px' }}>
            <div style={{ color: '#c62828', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>Errors:</div>
            {downloadStatus.errors.map((error, idx) => (
              <div key={idx} style={{ color: '#c62828', fontSize: '0.875rem' }}>{error}</div>
            ))}
          </div>
        )}
      </div>
      
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', color: '#333' }}>Infrastructure</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {data.proxy && (
            <ServerCard
              server={data.proxy}
              onStart={handleStart}
              onStop={handleStop}
              onViewLogs={() => setLogViewer({ serverId: data.proxy.id, serverName: data.proxy.name })}
              actionLoading={actionLoading}
            />
          )}
          {data.limbo && (
            <ServerCard
              server={data.limbo}
              onStart={handleStart}
              onStop={handleStop}
              onViewLogs={() => setLogViewer({ serverId: data.limbo.id, serverName: data.limbo.name })}
              actionLoading={actionLoading}
            />
          )}
        </div>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', color: '#333' }}>Services</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {data.services && data.services.length > 0 ? (
            data.services.map(service => (
              <ServerCard
                key={service.id}
                server={service}
                onStart={handleStart}
                onStop={handleStop}
                onViewLogs={() => setLogViewer({ serverId: service.id, serverName: service.name })}
                actionLoading={actionLoading}
              />
            ))
          ) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>No services available</div>
          )}
        </div>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', color: '#333' }}>Game Servers</h2>
        {data.gameservers && Object.keys(data.gameservers).length > 0 ? (
          Object.entries(data.gameservers).map(([serverName, server]) => (
          <div key={serverName} style={{ marginBottom: '2rem', border: '1px solid #ddd', borderRadius: '8px', padding: '1.5rem', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#333' }}>{serverName}</h3>
              <button
                onClick={() => addInstance(serverName)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#2196f3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}
              >
                + Add Instance
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
              {server.instances.map(instance => (
                <InstanceCard
                  key={instance.id}
                  instance={instance}
                  serverName={serverName}
                  onStart={() => handleStart(instance.id)}
                  onStop={() => handleStop(instance.id)}
                  onViewLogs={() => setLogViewer({ serverId: instance.id, serverName: `${serverName} Instance ${instance.instance}` })}
                  onRemove={() => removeInstance(serverName, instance.instance)}
                  canRemove={server.instances.length > 1}
                  actionLoading={actionLoading}
                />
              ))}
            </div>
          </div>
        ))
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>No game servers available</div>
        )}
      </div>

      {logViewer && (
        <LogViewer
          serverId={logViewer.serverId}
          serverName={logViewer.serverName}
          isOpen={true}
          onClose={() => setLogViewer(null)}
        />
      )}
    </div>
  )
}

function ServerCard({ server, onStart, onStop, onViewLogs, onSelect, isSelected, actionLoading }: {
  server: { id: string; name: string; running: boolean }
  onStart: (id: string) => void
  onStop: (id: string) => void
  onViewLogs: () => void
  onSelect?: () => void
  isSelected?: boolean
  actionLoading: string | null
}) {
  return (
    <div
      style={{
        border: `2px solid ${isSelected ? '#2196f3' : '#ddd'}`,
        borderRadius: '8px',
        padding: '1.25rem',
        backgroundColor: isSelected ? '#e3f2fd' : '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        transition: 'transform 0.2s, box-shadow 0.2s',
        cursor: onSelect ? 'pointer' : 'default'
      }}
      onClick={onSelect}
      onMouseEnter={(e) => {
        if (!onSelect) {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)'
        }
      }}
      onMouseLeave={(e) => {
        if (!onSelect) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'
        }
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ flex: 1 }}>
          {onSelect && (
            <input
              type="checkbox"
              checked={isSelected || false}
              onChange={onSelect}
              onClick={(e) => e.stopPropagation()}
              style={{ marginRight: '0.5rem', cursor: 'pointer' }}
            />
          )}
          <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', fontSize: '1.125rem', color: '#333', display: 'inline' }}>{server.name || 'Unknown'}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
            <div
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: server.running ? '#4caf50' : '#999'
              }}
            />
            <div style={{ fontSize: '0.875rem', color: server.running ? '#2e7d32' : '#666', fontWeight: '500' }}>
              {server.running ? 'Running' : 'Stopped'}
            </div>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {server.running ? (
          <>
            <button
              onClick={() => onStop(server.id)}
              disabled={actionLoading === server.id}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading === server.id ? 'not-allowed' : 'pointer',
                opacity: actionLoading === server.id ? 0.6 : 1,
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              {actionLoading === server.id ? 'Stopping...' : 'Stop'}
            </button>
            <button
              onClick={onViewLogs}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#607d8b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              View Logs
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => onStart(server.id)}
              disabled={actionLoading === server.id}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading === server.id ? 'not-allowed' : 'pointer',
                opacity: actionLoading === server.id ? 0.6 : 1,
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              {actionLoading === server.id ? 'Starting...' : 'Start'}
            </button>
            <button
              onClick={onViewLogs}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#607d8b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              View Logs
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function InstanceCard({ instance, serverName, onStart, onStop, onViewLogs, onRemove, canRemove, actionLoading }: {
  instance: Instance
  serverName: string
  onStart: () => void
  onStop: () => void
  onViewLogs: () => void
  onRemove: () => void
  canRemove: boolean
  actionLoading: string | null
}) {
  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderRadius: '6px',
        padding: '1rem',
        backgroundColor: instance.running ? '#e8f5e9' : '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        transition: 'transform 0.2s'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: '0.25rem', fontSize: '1rem', color: '#333' }}>
            Instance {instance.instance}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: instance.running ? '#4caf50' : '#999'
              }}
            />
            <div style={{ fontSize: '0.875rem', color: instance.running ? '#2e7d32' : '#666' }}>
              {instance.running ? 'Running' : 'Stopped'}
            </div>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {instance.running ? (
          <>
            <button
              onClick={onStop}
              disabled={actionLoading === instance.id}
              style={{
                padding: '0.4rem 0.8rem',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading === instance.id ? 'not-allowed' : 'pointer',
                opacity: actionLoading === instance.id ? 0.6 : 1,
                fontSize: '0.875rem'
              }}
            >
              {actionLoading === instance.id ? '...' : 'Stop'}
            </button>
            <button
              onClick={onViewLogs}
              style={{
                padding: '0.4rem 0.8rem',
                backgroundColor: '#607d8b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              Logs
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onStart}
              disabled={actionLoading === instance.id}
              style={{
                padding: '0.4rem 0.8rem',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading === instance.id ? 'not-allowed' : 'pointer',
                opacity: actionLoading === instance.id ? 0.6 : 1,
                fontSize: '0.875rem'
              }}
            >
              {actionLoading === instance.id ? '...' : 'Start'}
            </button>
            <button
              onClick={onViewLogs}
              style={{
                padding: '0.4rem 0.8rem',
                backgroundColor: '#607d8b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              Logs
            </button>
            {canRemove && (
              <button
                onClick={onRemove}
                disabled={actionLoading === instance.id}
                style={{
                  padding: '0.4rem 0.8rem',
                  backgroundColor: '#ff9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: actionLoading === instance.id ? 'not-allowed' : 'pointer',
                  opacity: actionLoading === instance.id ? 0.6 : 1,
                  fontSize: '0.875rem'
                }}
              >
                Remove
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
