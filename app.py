"""
JSON Comparison App - Compares user input JSON with data extracted from PDF invoices.
Uses Azure Document Intelligence and Azure OpenAI with keyless authentication.
"""

import json
import os
import re
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()


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


def extract_text_from_pdf(client: DocumentIntelligenceClient, pdf_path: str) -> dict:
    """Extract structured data from PDF using Document Intelligence prebuilt-invoice model."""
    import base64
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # SDK 1.0.0+ requires AnalyzeDocumentRequest with base64-encoded bytes
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


def get_user_input_json() -> dict:
    """Get JSON input from user via console."""
    print("\n" + "="*60)
    print("Enter your JSON data (data A). Example format:")
    print(json.dumps({
        "seller_name": "Jan Kowalski",
        "buyer_name": "Euro Trans Jan Pawlak",
        "date": "2026-03-26",
        "product_sku": 4324325,
        "amount": 35
    }, indent=2))
    print("="*60)
    print("\nPaste your JSON (press Enter twice when done):")
    
    lines = []
    while True:
        line = input()
        if line == "":
            if lines:
                break
        else:
            lines.append(line)
    
    json_str = "\n".join(lines)
    return json.loads(json_str)


def process_invoice(pdf_path: str, input_json: dict) -> dict:
    """
    Main processing function that:
    1. Extracts data from PDF using Document Intelligence
    2. Structures the data using Azure OpenAI
    3. Anonymizes names in both datasets
    4. Compares the two JSONs
    
    Returns a comparison result suitable for database storage.
    """
    print(f"\n[1/4] Extracting data from PDF: {pdf_path}")
    di_client = get_document_intelligence_client()
    extracted_data = extract_text_from_pdf(di_client, pdf_path)
    
    print("[2/4] Structuring extracted data with LLM...")
    openai_client = get_openai_client()
    extracted_json = extract_json_with_llm(openai_client, extracted_data, input_json)
    print(f"  Extracted: {json.dumps(extracted_json, ensure_ascii=False)}")
    
    print("[3/4] Anonymizing names...")
    anonymized_input = anonymize_data(input_json)
    anonymized_extracted = anonymize_data(extracted_json)
    print(f"  Input anonymized: {json.dumps(anonymized_input, ensure_ascii=False)}")
    print(f"  Extracted anonymized: {json.dumps(anonymized_extracted, ensure_ascii=False)}")
    
    print("[4/4] Comparing data...")
    comparison_result = compare_json(anonymized_input, anonymized_extracted)
    
    return comparison_result


def main():
    """Main entry point."""
    print("="*60)
    print("PDF Invoice JSON Comparison Tool")
    print("="*60)
    
    # Default PDF path
    pdf_path = "faktura_example.pdf"
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        print(f"\nError: PDF file not found: {pdf_path}")
        pdf_path = input("Enter the path to your PDF file: ").strip()
        if not Path(pdf_path).exists():
            print(f"Error: File not found: {pdf_path}")
            return
    
    # Get user input JSON
    try:
        input_json = get_user_input_json()
        print(f"\nReceived input JSON: {json.dumps(input_json, ensure_ascii=False)}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input - {e}")
        return
    
    # Process the invoice
    try:
        result = process_invoice(pdf_path, input_json)
        
        # Save result to file for database import
        output_file = "comparison_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Overall Match: {'✓ YES' if result['all_match'] else '✗ NO'}")
        print("\nField-by-field comparison:")
        for field, data in result["field_comparison"].items():
            status = "✓" if data["match"] else "✗"
            print(f"  {status} {field}: Input='{data['value_input']}' | Extracted='{data['value_extracted']}'")
        
        print(f"\nFull result saved to: {output_file}")
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        raise


if __name__ == "__main__":
    main()
