# PDF Invoice JSON Comparison Tool

Compares user-provided JSON data with data extracted from PDF invoices using Azure Document Intelligence and Azure OpenAI.

## Features

- Extracts structured data from PDF invoices using Azure Document Intelligence (`prebuilt-invoice` model)
- Uses Azure OpenAI to map extracted fields to your JSON schema
- Anonymizes names (keeps first 2 and last 2 characters, replaces middle with `*`)
- Generates field-by-field comparison suitable for database storage

## Demo

https://github.com/aganiezgoda/json_comparison/raw/master/recording.mp4

## Prerequisites

- Python 3.10+
- Azure Document Intelligence resource
- Azure OpenAI resource with a deployed model (e.g., `gpt-4o`)
- Azure CLI logged in (`az login`) for keyless authentication

## Setup

1. Create and activate virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Configure environment variables - copy `.env.example` to `.env` and fill in your values:
   ```
   DOCUMENT_INTELLIGENCE_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
   AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   ```

4. Place your PDF invoice in the project folder (default: `faktura_example.pdf`)

## Usage

```powershell
python app.py
```

Paste your JSON when prompted, then press Enter twice:

```json
{
  "seller_name": "Jan Kowalski",
  "buyer_name": "Euro Trans Jan Pawlak",
  "date": "2026-03-26",
  "product_sku": 4324325,
  "amount": 35
}
```

## Output

The app generates `comparison_result.json` with the following structure:

```json
{
  "data_input": {
    "seller_name": "Ja********ki",
    "buyer_name": "Eu*****************ak",
    "date": "2026-03-26",
    "product_sku": 4324325,
    "amount": 35
  },
  "data_extracted": {
    "seller_name": "Ja********ki",
    "buyer_name": "Eu*****************ak",
    "date": "2024-04-15",
    "product_sku": null,
    "amount": 1
  },
  "field_comparison": {
    "date": {
      "value_a": "2026-03-26",
      "value_b": "2024-04-15",
      "match": false
    },
    "buyer_name": {
      "value_a": "Eu*****************ak",
      "value_b": "Eu*****************ak",
      "match": true
    },
    "product_sku": {
      "value_a": 4324325,
      "value_b": null,
      "match": false
    },
    "seller_name": {
      "value_a": "Ja********ki",
      "value_b": "Ja********ki",
      "match": true
    },
    "amount": {
      "value_a": 35,
      "value_b": 1,
      "match": false
    }
  },
  "all_match": false
}
```

## Database Integration

The output dictionary is designed for easy database insertion:

| Field | Description |
|-------|-------------|
| `data_input` | Anonymized user-provided JSON |
| `data_extracted` | Anonymized data extracted from PDF |
| `field_comparison` | Per-field comparison with match status |
| `all_match` | `true` if all fields match, `false` otherwise |

## Authentication

Uses `DefaultAzureCredential` (keyless authentication). Ensure you're logged in via:
```powershell
az login
```
