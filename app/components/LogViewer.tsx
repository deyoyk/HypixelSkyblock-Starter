'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { API_URL } from '../lib/api'

interface LogViewerProps {
  serverId: string
  serverName: string
  isOpen: boolean
  onClose: () => void
}

export default function LogViewer({ serverId, serverName, isOpen, onClose }: LogViewerProps) {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [lines, setLines] = useState(500)
  const logContainerRef = useRef<HTMLDivElement>(null)

  const fetchLogs = useCallback(async () => {
    if (!isOpen) return
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/servers/${serverId}/logs?lines=${lines}&tail=true`)
      const data = await response.json()
      if (response.ok) {
        setLogs(data.logs || [])
      }
    } catch (error) {
      console.error('Error fetching logs:', error)
    } finally {
      setLoading(false)
    }
  }, [isOpen, serverId, lines])

  useEffect(() => {
    if (!isOpen) return
    
    fetchLogs()
    const interval = setInterval(fetchLogs, 2000)
    return () => clearInterval(interval)
  }, [isOpen, serverId, lines, fetchLogs])

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const filteredLogs = logs.filter(log => 
    searchTerm === '' || log.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getLogLevel = (line: string): string => {
    const upper = line.toUpperCase()
    if (upper.includes('ERROR') || upper.includes('FATAL')) return 'error'
    if (upper.includes('WARN')) return 'warn'
    if (upper.includes('INFO')) return 'info'
    if (upper.includes('DEBUG')) return 'debug'
    return 'default'
  }

  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#1e1e1e',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '1200px',
          height: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid #333',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#252526'
          }}
        >
          <div>
            <h2 style={{ margin: 0, color: '#fff', fontSize: '1.25rem' }}>{serverName} - Logs</h2>
            <div style={{ fontSize: '0.875rem', color: '#999', marginTop: '0.25rem' }}>
              {filteredLogs.length} of {logs.length} lines
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#3e3e42',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            Close
          </button>
        </div>

        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid #333',
            display: 'flex',
            gap: '1rem',
            alignItems: 'center',
            backgroundColor: '#252526',
            flexWrap: 'wrap'
          }}
        >
          <input
            type="text"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '0.5rem',
              backgroundColor: '#3e3e42',
              color: '#fff',
              border: '1px solid #555',
              borderRadius: '4px',
              fontSize: '0.875rem'
            }}
          />
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            style={{
              padding: '0.5rem',
              backgroundColor: '#3e3e42',
              color: '#fff',
              border: '1px solid #555',
              borderRadius: '4px',
              fontSize: '0.875rem'
            }}
          >
            <option value={100}>Last 100 lines</option>
            <option value={500}>Last 500 lines</option>
            <option value={1000}>Last 1000 lines</option>
            <option value={5000}>Last 5000 lines</option>
          </select>
          <label style={{ color: '#fff', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          <button
            onClick={fetchLogs}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#007acc',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '0.875rem',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        <div
          ref={logContainerRef}
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '1rem',
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '0.875rem',
            lineHeight: '1.5',
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4'
          }}
        >
          {filteredLogs.length === 0 ? (
            <div style={{ color: '#999', textAlign: 'center', padding: '2rem' }}>
              {searchTerm ? 'No logs match your search' : 'No logs available'}
            </div>
          ) : (
            filteredLogs.map((log, index) => {
              const level = getLogLevel(log)
              const colors: { [key: string]: { bg: string; text: string } } = {
                error: { bg: '#3a1d1d', text: '#f48771' },
                warn: { bg: '#3a2f1d', text: '#dcdcaa' },
                info: { bg: '#1d3a3a', text: '#4ec9b0' },
                debug: { bg: '#2d2d2d', text: '#9cdcfe' },
                default: { bg: 'transparent', text: '#d4d4d4' }
              }
              const style = colors[level] || colors.default

              return (
                <div
                  key={index}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: style.bg,
                    color: style.text,
                    borderLeft: level !== 'default' ? `3px solid ${style.text}` : 'none',
                    marginBottom: '0.125rem',
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  <span style={{ color: '#858585', marginRight: '0.5rem' }}>
                    {String(index + 1).padStart(5, '0')}
                  </span>
                  {log}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

