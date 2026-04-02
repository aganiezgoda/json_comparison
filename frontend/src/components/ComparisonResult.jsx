import './ComparisonResult.css'

function ComparisonResult({ result }) {
  const { data_input, data_extracted, field_comparison, all_match } = result

  const matchCount = Object.values(field_comparison).filter(f => f.match).length
  const totalFields = Object.keys(field_comparison).length

  return (
    <div className="comparison-result">
      <div className={`result-header ${all_match ? 'success' : 'mismatch'}`}>
        <div className="result-icon">
          {all_match ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          )}
        </div>
        <div className="result-summary">
          <h2>{all_match ? 'All Fields Match!' : 'Differences Found'}</h2>
          <p>{matchCount} of {totalFields} fields match</p>
        </div>
      </div>

      <div className="comparison-table-container">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Your Data (Input)</th>
              <th>PDF Data (Extracted)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(field_comparison).map(([field, data]) => (
              <tr key={field} className={data.match ? 'match' : 'mismatch'}>
                <td className="field-name">{formatFieldName(field)}</td>
                <td className="field-value">
                  <code>{formatValue(data.value_input)}</code>
                </td>
                <td className="field-value">
                  <code>{formatValue(data.value_extracted)}</code>
                </td>
                <td className="field-status">
                  {data.match ? (
                    <span className="status-badge match">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      Match
                    </span>
                  ) : (
                    <span className="status-badge mismatch">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                      Differs
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="json-output-section">
        <h3>Full Comparison Result (JSON)</h3>
        <pre className="json-output">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    </div>
  )
}

function formatFieldName(field) {
  return field
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatValue(value) {
  if (value === null || value === undefined) {
    return 'null'
  }
  return String(value)
}

export default ComparisonResult
