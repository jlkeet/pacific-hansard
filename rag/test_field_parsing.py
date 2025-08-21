#!/usr/bin/env python3
"""Test field parsing logic"""

# Test the exact logic from the search service
doc = {
    'id': '2_0',
    'document_id': [2],
    'title': ['Hansard Oral Question 1'],
    'source': ['Fiji'],
    'date': ['2021-02-10T00:00:00Z'],
    'document_type': ['oral_question'],
    'chunk_index': [0],
    'token_count': [1098],
    'content': ['Some content here'],
    'score': 0.42078668
}

def get_field_value(field_name, default=''):
    value = doc.get(field_name, default)
    return value[0] if isinstance(value, list) and len(value) > 0 else value

print("Testing field parsing:")
print(f"chunk_index raw: {doc.get('chunk_index')} (type: {type(doc.get('chunk_index'))})")

chunk_idx = get_field_value('chunk_index', 0)
print(f"chunk_idx after get_field_value: {chunk_idx} (type: {type(chunk_idx)})")

chunk_idx = chunk_idx if chunk_idx is not None else 0
print(f"chunk_idx after null check: {chunk_idx} (type: {type(chunk_idx)})")

try:
    final_idx = int(chunk_idx)
    print(f"Final chunk_index: {final_idx} (type: {type(final_idx)})")
except Exception as e:
    print(f"Error converting to int: {e}")
    print(f"Value was: {chunk_idx} (type: {type(chunk_idx)})")
    
# Test other fields
print("\nOther fields:")
print(f"id: {get_field_value('id')}")
print(f"content: {get_field_value('content')[:50]}...")
print(f"source: {get_field_value('source')}")