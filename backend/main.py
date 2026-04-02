"""
FastAPI Backend for JSON Comparison App.
Compares user input JSON with data extracted from PDF invoices.
Uses Azure Document Intelligence and Azure OpenAI with keyless authentication.
"""

import json
import os
import base64
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import AzureOpenAI
from pathlib import Path

# Load environment variables (check parent directory too for shared .env)
env_file = Path(__file__).parent / ".env"
if not env_file.exists():
    env_file = Path(__file__).parent.parent / ".env"
load_dotenv(env_file)

app = FastAPI(
    title="PDF Invoice JSON Comparison API",
    description="Compare user-provided JSON with data extracted from PDF invoices",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class FieldComparison(BaseModel):
    value_input: Optional[str | int | float]
    value_extracted: Optional[str | int | float]
    match: bool


class ComparisonResult(BaseModel):
    data_input: dict
    data_extracted: dict
    field_comparison: dict[str, FieldComparison]
    all_match: bool


def get_document_intelligence_client() -> DocumentIntelligenceClient:
    """Create Document Intelligence client with keyless authentication."""
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not endpoint:
        raise ValueError("DOCUMENT_INTELLIGENCE_ENDPOINT not set in .env")
    
    credential = DefaultAzureCredential()
    return DocumentIntelligenceClient(endpoint=endpoint, credential=credential)


def get_openai_client() -> AzureOpenAI:
    """Create Azure OpenAI client with keyless authentication."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT not set in .env")
    
    credential = DefaultAzureCredential()
    token_provider = lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token
    
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-06-01"
    )


def extract_text_from_pdf(client: DocumentIntelligenceClient, pdf_bytes: bytes) -> dict:
    """Extract structured data from PDF using Document Intelligence prebuilt-invoice model."""
    base64_source = base64.b64encode(pdf_bytes).decode("utf-8")
    
    poller = client.begin_analyze_document(
        model_id="prebuilt-invoice",
        body={"base64Source": base64_source}
    )
    result: AnalyzeResult = poller.result()
    
    # Extract invoice fields
    extracted_data = {
        "raw_content": result.content,
        "invoices": []
    }
    
    if result.documents:
        for doc in result.documents:
            invoice_data = {}
            if doc.fields:
                for field_name, field in doc.fields.items():
                    if field.value_string:
                        invoice_data[field_name] = field.value_string
                    elif field.value_number:
                        invoice_data[field_name] = field.value_number
                    elif field.value_date:
                        invoice_data[field_name] = str(field.value_date)
                    elif field.content:
                        invoice_data[field_name] = field.content
            extracted_data["invoices"].append(invoice_data)
    
    return extracted_data


def extract_json_with_llm(openai_client: AzureOpenAI, extracted_data: dict, target_schema: dict) -> dict:
    """Use Azure OpenAI to structure extracted PDF data into the target JSON schema."""
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    
    schema_fields = list(target_schema.keys())
    
    system_prompt = f"""You are a data extraction assistant. Given raw extracted invoice data, 
extract and return a JSON object with exactly these fields: {schema_fields}.

Rules:
- seller_name: The name of the seller/vendor
- buyer_name: The name of the buyer/customer  
- date: The invoice date in YYYY-MM-DD format
- product_sku: The product SKU/code (as a number if possible)
- amount: The quantity/amount (as a number)

Return ONLY valid JSON, no markdown formatting or explanations."""

    user_message = f"""Extract data from this invoice content:

Raw text content:
{extracted_data.get('raw_content', '')}

Structured invoice fields:
{json.dumps(extracted_data.get('invoices', []), indent=2, ensure_ascii=False)}

Target schema example:
{json.dumps(target_schema, indent=2, ensure_ascii=False)}"""

    response = openai_client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def anonymize_name(name: str) -> str:
    """
    Anonymize a name by keeping first 2 and last 2 characters, replacing rest with asterisks.
    Example: 'Jan Kowalski' -> 'Ja********ki'
    """
    if not name or len(name) <= 4:
        return name
    
    first_two = name[:2]
    last_two = name[-2:]
    middle_length = len(name) - 4
    
    return f"{first_two}{'*' * middle_length}{last_two}"


def anonymize_data(data: dict, name_fields: list[str] = None) -> dict:
    """Anonymize specified name fields in the data dictionary."""
    if name_fields is None:
        name_fields = ["seller_name", "buyer_name"]
    
    anonymized = data.copy()
    for field in name_fields:
        if field in anonymized and isinstance(anonymized[field], str):
            anonymized[field] = anonymize_name(anonymized[field])
    
    return anonymized


def compare_json(data_a: dict, data_b: dict) -> dict:
    """
    Compare two JSON objects and generate a comparison report.
    Returns a dictionary structure suitable for database storage.
    """
    comparison = {}
    all_fields = set(data_a.keys()) | set(data_b.keys())
    
    for field in all_fields:
        value_input = data_a.get(field)
        value_extracted = data_b.get(field)
        
        # Normalize values for comparison (handle type differences)
        normalized_a = str(value_input).strip() if value_input is not None else None
        normalized_b = str(value_extracted).strip() if value_extracted is not None else None
        
        match = normalized_a == normalized_b
        
        comparison[field] = {
            "value_input": value_input,
            "value_extracted": value_extracted,
            "match": match
        }
    
    # Calculate overall match
    all_match = all(field_data["match"] for field_data in comparison.values())
    
    return {
        "data_input": data_a,
        "data_extracted": data_b,
        "field_comparison": comparison,
        "all_match": all_match
    }


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "PDF Invoice JSON Comparison API"}


@app.post("/api/compare", response_model=ComparisonResult)
async def compare_invoice(
    pdf_file: UploadFile = File(..., description="PDF invoice file to analyze"),
    json_data: str = Form(..., description="JSON string with expected invoice data")
):
    """
    Compare user-provided JSON with data extracted from a PDF invoice.
    
    Steps:
    1. Extract data from PDF using Document Intelligence
    2. Structure the data using Azure OpenAI
    3. Anonymize names in both datasets
    4. Compare the two JSONs and return results
    """
    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Parse JSON input
    try:
        input_json = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    try:
        # Read PDF bytes
        pdf_bytes = await pdf_file.read()
        
        # Extract data from PDF
        di_client = get_document_intelligence_client()
        extracted_data = extract_text_from_pdf(di_client, pdf_bytes)
        
        # Structure with LLM
        openai_client = get_openai_client()
        extracted_json = extract_json_with_llm(openai_client, extracted_data, input_json)
        
        # Anonymize names
        anonymized_input = anonymize_data(input_json)
        anonymized_extracted = anonymize_data(extracted_json)
        
        # Compare
        result = compare_json(anonymized_input, anonymized_extracted)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
