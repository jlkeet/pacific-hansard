#!/usr/bin/env python3

def test_title_cleanup():
    # Test the title cleanup logic
    test_titles = [
        "PNG Hansard Part 4 - ANSWERS TO PREVIOUS QUESTIONS",
        "PNG Hansard Part 5 - MINISTRY OF TREASURY",
        "Hansard Oral Question - Some Question",
        "Regular Title"
    ]
    
    for original_title in test_titles:
        title = original_title
        
        # Apply the cleanup logic from pipelines_enhanced.py
        if title and 'PNG Hansard Part' in title:
            # Extract just the meaningful part after the dash
            parts = title.split(' - ', 1)
            if len(parts) > 1:
                title = parts[1].strip()
        
        print(f"Original: {original_title}")
        print(f"Cleaned:  {title}")
        print()

if __name__ == "__main__":
    test_title_cleanup()