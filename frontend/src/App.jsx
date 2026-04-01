import { useState } from 'react'
import FileUpload from './components/FileUpload'
import JsonInput from './components/JsonInput'
import ComparisonResult from './components/ComparisonResult'
import './App.css'

function App() {
  const [pdfFile, setPdfFile] = useState(null)
  const [jsonData, setJsonData] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    if (!pdfFile) {
      setError('Please upload a PDF file')
      return
    }
    if (!jsonData.trim()) {
      setError('Please enter JSON data')
      return
    }

    // Validate JSON
    try {
      JSON.parse(jsonData)
    } catch (e) {
      setError('Invalid JSON format: ' + e.message)
      return
    }

    setError(null)
    setLoading(true)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('pdf_file', pdfFile)
      formData.append('json_data', jsonData)

      const response = await fetch('/api/compare', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Server error')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setPdfFile(null)
    setJsonData('')
    setResult(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
            <h1>Invoice Comparison</h1>
          </div>
          <p className="subtitle">Compare PDF invoice data with your JSON records</p>
        </div>
      </header>

      <main className="main">
        {!result ? (
          <div className="input-section">
            <div className="cards-container">
              <div className="card">
                <div className="card-header">
                  <span className="step-badge">1</span>
                  <h2>Upload PDF Invoice</h2>
                </div>
                <FileUpload file={pdfFile} onFileChange={setPdfFile} />
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="step-badge">2</span>
                  <h2>Enter JSON Data</h2>
                </div>
                <JsonInput value={jsonData} onChange={setJsonData} />
              </div>
            </div>

            {error && (
              <div className="error-message">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            <button
              className="submit-button"
              onClick={handleSubmit}
              disabled={loading || !pdfFile || !jsonData.trim()}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Processing...
                </>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                  Compare Data
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="result-section">
            <ComparisonResult result={result} />
            <button className="reset-button" onClick={handleReset}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              Start New Comparison
            </button>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Powered by Azure Document Intelligence & Azure OpenAI</p>
      </footer>
    </div>
  )
}

export default App
