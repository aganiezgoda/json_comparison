import './JsonInput.css'

const exampleJson = {
  seller_name: "Jan Kowalski",
  buyer_name: "Euro Trans Jan Pawlak",
  date: "2026-03-26",
  product_sku: 4324325,
  amount: 35
}

function JsonInput({ value, onChange }) {
  const handlePasteExample = () => {
    onChange(JSON.stringify(exampleJson, null, 2))
  }

  const formatJson = () => {
    try {
      const parsed = JSON.parse(value)
      onChange(JSON.stringify(parsed, null, 2))
    } catch (e) {
      // Invalid JSON, don't format
    }
  }

  const isValidJson = () => {
    if (!value.trim()) return true
    try {
      JSON.parse(value)
      return true
    } catch {
      return false
    }
  }

  return (
    <div className="json-input">
      <div className="json-toolbar">
        <button className="toolbar-button" onClick={handlePasteExample}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          Paste Example
        </button>
        <button className="toolbar-button" onClick={formatJson} disabled={!value.trim()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="4 7 4 4 20 4 20 7" />
            <line x1="9" y1="20" x2="15" y2="20" />
            <line x1="12" y1="4" x2="12" y2="20" />
          </svg>
          Format
        </button>
      </div>
      
      <textarea
        className={`json-textarea ${!isValidJson() ? 'invalid' : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Enter your JSON data here...\n\nExample:\n${JSON.stringify(exampleJson, null, 2)}`}
        spellCheck={false}
      />
      
      {!isValidJson() && (
        <div className="json-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          Invalid JSON syntax
        </div>
      )}
    </div>
  )
}

export default JsonInput
