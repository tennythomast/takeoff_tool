import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

# Import the test function
from rag_service.services.extraction.tests.test_text_extractor import test_extractor

# Run the test
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_text_test.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    test_extractor(file_path)
