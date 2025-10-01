#!/usr/bin/env python3
"""Test JSON output format"""

from flockparsecli import process_pdf
from pathlib import Path
import json

# Process one test PDF
pdf_path = 'testpdfs/antimatter_mysteries.pdf'
print(f'Processing {pdf_path}...\n')
process_pdf(pdf_path)

# Show the JSON output
json_file = Path('converted_files/antimatter_mysteries.json')
if json_file.exists():
    with open(json_file, 'r') as f:
        data = json.load(f)

    print('\n' + '='*60)
    print('📄 JSON Output Structure:')
    print('='*60)

    # Show structure without full content
    preview = {
        "filename": data.get("filename"),
        "original_path": data.get("original_path"),
        "processed_date": data.get("processed_date"),
        "character_count": data.get("character_count"),
        "word_count": data.get("word_count"),
        "title": data.get("title"),
        "content_preview": data.get("content", "")[:200] + "...",
        "metadata": data.get("metadata")
    }

    print(json.dumps(preview, indent=2))
    print(f'\n✅ Full JSON saved to: {json_file}')
else:
    print('❌ JSON file not found')