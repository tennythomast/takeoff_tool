#!/usr/bin/env python
"""
Script to check for potential async ORM issues in the codebase.
This script scans Python files for patterns that might indicate improper async ORM usage.

Run this script inside the Docker container with:
docker-compose exec backend python scripts/check_async_orm.py
"""

import os
import re
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Patterns to look for
PATTERNS = {
    'alist': r'\.alist\(\)',  # Direct .alist() calls
    'sync_in_async': r'async\s+def.*?\n.*?(?<!sync_to_async).*?\.objects\.',  # ORM in async without sync_to_async
    'queryset_in_async': r'async\s+def.*?\n.*?(?<!await).*?QuerySet.*?',  # QuerySet in async without await
}

def scan_file(file_path):
    """Scan a single file for problematic patterns."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            for pattern_name, pattern in PATTERNS.items():
                matches = re.finditer(pattern, content, re.DOTALL)
                for match in matches:
                    # Get line number by counting newlines
                    line_number = content[:match.start()].count('\n') + 1
                    context = content[max(0, match.start() - 50):match.start() + 50]
                    issues.append({
                        'pattern': pattern_name,
                        'line': line_number,
                        'context': context.replace('\n', ' ').strip(),
                        'file': str(file_path)
                    })
    except Exception as e:
        logger.error(f"Error scanning {file_path}: {str(e)}")
    
    return issues

def scan_directory(directory_path, exclude_dirs=None):
    """Recursively scan a directory for Python files with issues."""
    if exclude_dirs is None:
        exclude_dirs = ['venv', 'env', '.git', '__pycache__', 'migrations']
    
    all_issues = []
    directory = Path(directory_path)
    
    for path in directory.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in str(path) for excluded in exclude_dirs):
            continue
        
        file_issues = scan_file(path)
        all_issues.extend(file_issues)
    
    return all_issues

def main():
    """Main function to scan the codebase for async ORM issues."""
    logger.info("Scanning for potential async ORM issues...")
    
    # Determine the backend directory
    if os.path.exists('/app/backend'):
        # Running in Docker
        backend_dir = '/app/backend'
    else:
        # Running locally
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
    
    logger.info(f"Scanning directory: {backend_dir}")
    
    issues = scan_directory(backend_dir)
    
    if issues:
        logger.warning(f"Found {len(issues)} potential async ORM issues:")
        
        # Group by pattern
        by_pattern = {}
        for issue in issues:
            pattern = issue['pattern']
            if pattern not in by_pattern:
                by_pattern[pattern] = []
            by_pattern[pattern].append(issue)
        
        # Print summary by pattern
        for pattern, pattern_issues in by_pattern.items():
            logger.warning(f"\n{pattern} issues ({len(pattern_issues)}):")
            for issue in pattern_issues:
                logger.warning(f"  {issue['file']}:{issue['line']} - {issue['context']}")
    else:
        logger.info("No potential async ORM issues found!")
    
    return len(issues)

if __name__ == "__main__":
    sys.exit(main())
