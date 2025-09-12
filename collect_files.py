#!/usr/bin/env python3
"""
Script to collect all .py and .yaml files into clipboard with headers.
Respects .gitignore rules and excludes ignored files, also excludes itself..
"""

import os
import sys
from pathlib import Path
import fnmatch
from pathlib import Path
import pyperclip


SCRIPT_PATH = Path(__file__).resolve()  # add this near the imports

def parse_gitignore(gitignore_path):
    """Parse .gitignore file and return list of patterns."""
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    
    with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                patterns.append(line)
    
    return patterns


def is_ignored(file_path, root_dir, gitignore_patterns):
    """Check if a file should be ignored based on gitignore patterns."""
    # Get relative path from root
    try:
        rel_path = os.path.relpath(file_path, root_dir)
        rel_path = rel_path.replace('\\', '/')  # Use forward slashes for consistency
    except ValueError:
        return False
    
    # Check each pattern
    for pattern in gitignore_patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            dir_pattern = pattern[:-1]
            # Check if any parent directory matches
            path_parts = rel_path.split('/')
            for i in range(len(path_parts)):
                partial_path = '/'.join(path_parts[:i+1])
                if fnmatch.fnmatch(partial_path, dir_pattern) or fnmatch.fnmatch(path_parts[i], dir_pattern):
                    return True
        else:
            # File pattern
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # Also check just the filename
            filename = os.path.basename(rel_path)
            if fnmatch.fnmatch(filename, pattern):
                return True
    
    return False


def collect_files():
    """Main function to collect files and copy to clipboard."""
    root_dir = os.getcwd()
    gitignore_path = os.path.join(root_dir, '.gitignore')
    
    # Parse .gitignore patterns
    gitignore_patterns = parse_gitignore(gitignore_path)
    print(f"Found {len(gitignore_patterns)} gitignore patterns")
    
    # Extensions to collect
    target_extensions = {'.py', '.yaml', '.yml'}
    
    collected_content = []
    file_count = 0
    
    # Walk through all directories
    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories
        dirs_to_remove = []
        for d in dirs:
            dir_path = os.path.join(root, d)
            if is_ignored(dir_path, root_dir, gitignore_patterns):
                dirs_to_remove.append(d)
        
        for d in dirs_to_remove:
            dirs.remove(d)
        
        # Process files
        for file in files:

            file_path = os.path.join(root, file)

            # exclude this script itself
            try:
                if Path(file_path).resolve() == SCRIPT_PATH:
                    continue
            except Exception:
                # fallback for platforms/filesystems without resolve/samefile support
                if os.path.abspath(file_path) == str(SCRIPT_PATH):
                    continue  

            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Skip if not target extension
            if file_ext not in target_extensions:
                continue
            
            # Skip if ignored
            if is_ignored(file_path, root_dir, gitignore_patterns):
                print(f"Skipping ignored file: {file_path}")
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Create header with absolute path
                abs_path = os.path.abspath(file_path)
                header = f"\n{'=' * 80}\n# FILE: {abs_path}\n{'=' * 80}\n\n"
                
                collected_content.append(header + content)
                file_count += 1
                print(f"Collected: {abs_path}")
                
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    if collected_content:
        # Join all content
        final_content = ''.join(collected_content)
        
        # Copy to clipboard
        try:
            pyperclip.copy(final_content)
            print(f"\n✓ Successfully copied {file_count} files to clipboard!")
            print(f"Total characters: {len(final_content):,}")
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            print("Content written to output.txt instead")
            with open('output.txt', 'w', encoding='utf-8') as f:
                f.write(final_content)
    else:
        print("No files found to collect.")


if __name__ == "__main__":
    try:
        collect_files()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
