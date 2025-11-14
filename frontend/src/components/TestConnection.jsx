
import { useState } from 'react';
import { api } from '../utils/api';

export default function TestConnection() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const testBackend = async () => {
    try {
      setError(null);
      setResult('Testing...');
      const response = await fetch('/api/health');
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err.message);
      setResult(null);
    }
  };

  return (
    <div style={{ 
      position: 'fixed', 
      top: '120px', 
      right: '20px', 
      background: 'rgba(0,0,0,0.95)', 
      color: 'white', 
      padding: '20px', 
      borderRadius: '8px',
      zIndex: 99999,
      maxWidth: '400px',
      border: '2px solid #4CAF50',
      boxShadow: '0 4px 20px rgba(76, 175, 80, 0.5)'
    }}>
      <h3 style={{ margin: '0 0 10px 0' }}>Backend Connection Test</h3>
      <button 
        onClick={testBackend}
        style={{
          padding: '10px 20px',
          background: '#4CAF50',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Test Backend Connection
      </button>
      {result && (
        <pre style={{ 
          marginTop: '10px', 
          background: '#1e1e1e', 
          padding: '10px', 
          borderRadius: '4px',
          overflow: 'auto',
          maxHeight: '300px'
        }}>
          {result}
        </pre>
      )}
      {error && (
        <div style={{ 
          marginTop: '10px', 
          color: '#ff6b6b',
          padding: '10px',
          background: 'rgba(255,0,0,0.1)',
          borderRadius: '4px'
        }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}
