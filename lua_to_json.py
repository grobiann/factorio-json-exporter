#!/usr/bin/env python3
"""
Factorio Lua to JSON Exporter - Improved version
Converts Factorio mod Lua data files to JSON format.
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import tkinter as tk
from tkinter import filedialog


def parse_lua_value(value_str: str) -> Any:
    """Parse a simple Lua value string."""
    value_str = value_str.strip()
    
    # Boolean
    if value_str == 'true':
        return True
    if value_str == 'false':
        return False
    if value_str == 'nil':
        return None
    
    # Number
    try:
        if '.' in value_str or 'e' in value_str.lower():
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass
    
    # String (remove quotes)
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    # Otherwise, return as is (identifiers, complex expressions, etc.)
    return value_str


def extract_tables_from_lua(content: str) -> List[str]:
    """Extract individual table definitions from all data:extend calls."""
    all_tables = []
    
    # Find all data:extend({ ... }) calls
    pattern = r'data:extend\s*\(\s*\{'
    
    # Search for all occurrences
    search_pos = 0
    while True:
        match = re.search(pattern, content[search_pos:])
        if not match:
            break
        
        # Adjust position to absolute position in content
        match_start = search_pos + match.start()
        match_end = search_pos + match.end()
        
        # Find the matching closing braces
        start = match_end - 1  # Position of opening {
        pos = start + 1
        brace_count = 1
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        # Extract the content between braces
        table_array_content = content[start+1:pos-1]
        
        # Split into individual table definitions
        current_table = []
        brace_count = 0
        in_string = False
        string_char = None
        escape_next = False
        
        for char in table_array_content:
            if escape_next:
                current_table.append(char)
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                current_table.append(char)
                continue
            
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
                current_table.append(char)
            elif in_string and char == string_char:
                in_string = False
                string_char = None
                current_table.append(char)
            elif not in_string:
                if char == '{':
                    if brace_count == 0:
                        # Start of a new table
                        current_table = [char]
                    else:
                        current_table.append(char)
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    current_table.append(char)
                    if brace_count == 0:
                        # End of current table
                        all_tables.append(''.join(current_table))
                        current_table = []
                elif brace_count > 0:
                    current_table.append(char)
            else:
                current_table.append(char)
        
        # Move search position forward to find next data:extend
        search_pos = pos
    
    return all_tables


def parse_lua_table(table_str: str) -> Any:
    """Parse a Lua table string into a Python dict or list."""
    table_str = table_str.strip()
    
    # Remove outer braces
    if table_str.startswith('{') and table_str.endswith('}'):
        table_str = table_str[1:-1]
    
    # Check if this is an array (no key=value pairs at the top level)
    # Look for the first non-comment, non-whitespace content
    is_array = True
    temp_pos = 0
    while temp_pos < len(table_str):
        # Skip whitespace
        while temp_pos < len(table_str) and table_str[temp_pos] in ' \t\n\r':
            temp_pos += 1
        if temp_pos >= len(table_str):
            break
        # Skip comments
        if table_str[temp_pos:temp_pos+2] == '--':
            while temp_pos < len(table_str) and table_str[temp_pos] != '\n':
                temp_pos += 1
            continue
        # Check if we have a key=value pattern
        key_check = re.match(r'([a-zA-Z_][a-zA-Z0-9_-]*)\s*=', table_str[temp_pos:])
        if key_check:
            is_array = False
        break
    
    if is_array and table_str.strip():
        # Parse as array
        result = []
        pos = 0
        
        while pos < len(table_str):
            # Skip whitespace and comments
            while pos < len(table_str) and table_str[pos] in ' \t\n\r':
                pos += 1
            
            if pos >= len(table_str):
                break
            
            # Skip comments
            if table_str[pos:pos+2] == '--':
                while pos < len(table_str) and table_str[pos] != '\n':
                    pos += 1
                continue
            
            # Parse array element
            if table_str[pos] == '{':
                # Element is a table
                brace_count = 0
                value_start = pos
                in_string = False
                string_char = None
                escape_next = False
                
                while pos < len(table_str):
                    if escape_next:
                        escape_next = False
                        pos += 1
                        continue
                    
                    if table_str[pos] == '\\' and in_string:
                        escape_next = True
                        pos += 1
                        continue
                    
                    if table_str[pos] in ['"', "'"] and not in_string:
                        in_string = True
                        string_char = table_str[pos]
                    elif in_string and table_str[pos] == string_char:
                        in_string = False
                        string_char = None
                    elif not in_string:
                        if table_str[pos] == '{':
                            brace_count += 1
                        elif table_str[pos] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                pos += 1
                                break
                    
                    pos += 1
                
                value_str = table_str[value_start:pos]
                try:
                    result.append(parse_lua_table(value_str))
                except:
                    result.append(value_str.strip())
            
            elif table_str[pos] in ['"', "'"]:
                # Element is a string
                quote = table_str[pos]
                pos += 1
                value_start = pos
                escape_next = False
                
                while pos < len(table_str):
                    if escape_next:
                        escape_next = False
                        pos += 1
                        continue
                    
                    if table_str[pos] == '\\':
                        escape_next = True
                        pos += 1
                        continue
                    
                    if table_str[pos] == quote:
                        break
                    
                    pos += 1
                
                result.append(table_str[value_start:pos])
                pos += 1  # Skip closing quote
            
            else:
                # Element is a number, boolean, or identifier
                value_start = pos
                brace_count = 0
                bracket_count = 0
                paren_count = 0
                in_string = False
                string_char = None
                old_pos = pos
                
                while pos < len(table_str):
                    char = table_str[pos]
                    
                    if char in ['"', "'"] and not in_string:
                        in_string = True
                        string_char = char
                    elif in_string and char == string_char:
                        in_string = False
                        string_char = None
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            if brace_count > 0:
                                brace_count -= 1
                            else:
                                break
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                        elif char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        elif char == ',' and brace_count == 0 and bracket_count == 0 and paren_count == 0:
                            break
                    
                    pos += 1
                
                # Prevent infinite loop: ensure pos has advanced
                if pos == old_pos:
                    pos += 1
                
                value_str = table_str[value_start:pos].strip()
                if value_str.endswith(','):
                    value_str = value_str[:-1].strip()
                
                if value_str:
                    result.append(parse_lua_value(value_str))
            
            # Skip comma if present
            while pos < len(table_str) and table_str[pos] in ', \t\n\r':
                pos += 1
        
        return result
    
    else:
        # Parse as dictionary
        result = {}
        pos = 0
        
        while pos < len(table_str):
            # Skip whitespace and comments
            while pos < len(table_str) and table_str[pos] in ' \t\n\r':
                pos += 1
            
            if pos >= len(table_str):
                break
            
            # Skip comments
            if table_str[pos:pos+2] == '--':
                # Skip to end of line
                while pos < len(table_str) and table_str[pos] != '\n':
                    pos += 1
                continue
            
            # Find the key
            key_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_-]*)\s*=', table_str[pos:])
            if not key_match:
                # Skip this character and continue
                pos += 1
                continue
            
            key = key_match.group(1)
            pos += key_match.end()
            
            # Skip whitespace after =
            while pos < len(table_str) and table_str[pos] in ' \t\n\r':
                pos += 1
            
            # Find the value
            if table_str[pos] == '{':
                # Value is a table/array
                brace_count = 0
                value_start = pos
                in_string = False
                string_char = None
                escape_next = False
                
                while pos < len(table_str):
                    if escape_next:
                        escape_next = False
                        pos += 1
                        continue
                    
                    if table_str[pos] == '\\' and in_string:
                        escape_next = True
                        pos += 1
                        continue
                    
                    if table_str[pos] in ['"', "'"] and not in_string:
                        in_string = True
                        string_char = table_str[pos]
                    elif in_string and table_str[pos] == string_char:
                        in_string = False
                        string_char = None
                    elif not in_string:
                        if table_str[pos] == '{':
                            brace_count += 1
                        elif table_str[pos] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                pos += 1
                                break
                    
                    pos += 1
                
                value_str = table_str[value_start:pos]
                # Try to parse as nested table
                if value_str.strip().startswith('{'):
                    try:
                        result[key] = parse_lua_table(value_str)
                    except:
                        result[key] = value_str.strip()
                else:
                    result[key] = value_str.strip()
            
            elif table_str[pos] in ['"', "'"]:
                # Value is a string
                quote = table_str[pos]
                pos += 1
                value_start = pos
                escape_next = False
                
                while pos < len(table_str):
                    if escape_next:
                        escape_next = False
                        pos += 1
                        continue
                    
                    if table_str[pos] == '\\':
                        escape_next = True
                        pos += 1
                        continue
                    
                    if table_str[pos] == quote:
                        break
                    
                    pos += 1
                
                result[key] = table_str[value_start:pos]
                pos += 1  # Skip closing quote
            
            else:
                # Value is a number, boolean, identifier, or complex expression
                value_start = pos
                brace_count = 0
                bracket_count = 0
                paren_count = 0
                in_string = False
                string_char = None
                old_pos = pos
                
                while pos < len(table_str):
                    char = table_str[pos]
                    
                    if char in ['"', "'"] and not in_string:
                        in_string = True
                        string_char = char
                    elif in_string and char == string_char:
                        in_string = False
                        string_char = None
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            if brace_count > 0:
                                brace_count -= 1
                            else:
                                break
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                        elif char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        elif char == ',' and brace_count == 0 and bracket_count == 0 and paren_count == 0:
                            break
                    
                    pos += 1
                
                # Prevent infinite loop: ensure pos has advanced
                if pos == old_pos:
                    pos += 1
                
                value_str = table_str[value_start:pos].strip()
                # Remove trailing comma if present
                if value_str.endswith(','):
                    value_str = value_str[:-1].strip()
                
                result[key] = parse_lua_value(value_str)
            
            # Skip comma if present
            while pos < len(table_str) and table_str[pos] in ', \t\n\r':
                pos += 1
        
        return result


def convert_lua_to_json(lua_file_path: str, output_file_path: Optional[str] = None) -> str:
    """
    Convert a Lua data file to JSON format.
    
    Args:
        lua_file_path: Path to the Lua file to convert
        output_file_path: Optional path for the output JSON file
    
    Returns:
        Path to the created JSON file
    """
    print(f"Reading {lua_file_path}...")
    
    # Read Lua file
    with open(lua_file_path, 'r', encoding='utf-8') as f:
        lua_content = f.read()
    
    print(f"Extracting tables...")
    
    # Extract tables
    table_strings = extract_tables_from_lua(lua_content)
    print(f"Found {len(table_strings)} table definitions")
    
    # Parse each table
    items = []
    for i, table_str in enumerate(table_strings, 1):
        print(f"Parsing table {i}/{len(table_strings)}...")
        try:
            parsed = parse_lua_table(table_str)
            items.append(parsed)
        except Exception as e:
            print(f"Warning: Failed to parse table {i}: {e}")
            # Include raw string as fallback
            items.append({"_raw": table_str, "_error": str(e)})
    
    # Generate output filename if not provided
    if output_file_path is None:
        lua_path = Path(lua_file_path)
        output_file_path = lua_path.parent / f"{lua_path.stem}.json"
    
    print(f"Writing {output_file_path}...")
    
    # Ensure output directory exists
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON file (overwrite if exists)
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    
    return str(output_file_path)


def select_files_gui() -> List[str]:
    """Open a file dialog to select Lua files."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    file_paths = filedialog.askopenfilenames(
        title="Select Lua files to convert",
        filetypes=[("Lua files", "*.lua"), ("All files", "*.*")]
    )
    
    return list(file_paths)


def select_folder_gui() -> Optional[str]:
    """Open a file dialog to select a folder."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    folder_path = filedialog.askdirectory(
        title="Select folder containing Lua files to convert"
    )
    
    return folder_path if folder_path else None


def find_lua_files_recursive(folder_path: str) -> List[str]:
    """Recursively find all .lua files in a folder and its subfolders."""
    lua_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.lua'):
                lua_files.append(os.path.join(root, file))
    return lua_files


def select_output_directory_gui() -> Optional[str]:
    """Open a file dialog to select output directory."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    directory = filedialog.askdirectory(
        title="Select output directory for JSON files"
    )
    
    return directory if directory else None


def main():
    """Main entry point."""
    print("Factorio Lua to JSON Exporter (Improved)")
    print("=" * 50)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Convert Factorio Lua data files to JSON format",
        epilog="Default: Select folder (recursive). Use --files to select individual files instead."
    )
    parser.add_argument(
        'paths',
        nargs='*',
        help='Lua files or folders to convert (command-line mode)'
    )
    parser.add_argument(
        '--files',
        action='store_true',
        help='Select individual files instead of folder (GUI mode)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output directory for JSON files (default: preserves folder structure)'
    )
    
    args = parser.parse_args()
    
    # Get input files
    lua_files = []
    input_base_path = None  # Base path for preserving folder structure
    
    if args.paths:
        # Process command-line arguments (files or folders)
        for path in args.paths:
            if os.path.isfile(path):
                lua_files.append(path)
            elif os.path.isdir(path):
                if input_base_path is None:
                    input_base_path = path
                print(f"Searching for .lua files in: {path}")
                found_files = find_lua_files_recursive(path)
                lua_files.extend(found_files)
                print(f"Found {len(found_files)} .lua file(s)")
    else:
        # GUI mode
        if args.files:
            # User explicitly wants to select individual files
            print("\nSelect Lua files to convert...")
            lua_files = select_files_gui()
        else:
            # Default: Select folder
            print("\nSelect folder containing Lua files...")
            folder_path = select_folder_gui()
            if folder_path:
                input_base_path = folder_path
                print(f"Selected folder: {folder_path}")
                print("Searching for .lua files...")
                lua_files = find_lua_files_recursive(folder_path)
                print(f"Found {len(lua_files)} .lua file(s)")
            else:
                print("No folder selected.")
    
    if not lua_files:
        print("No files selected. Exiting.")
        return
    
    # Get output directory
    output_dir = None
    if args.output:
        output_dir = args.output
        if not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
    elif not args.paths:
        # Only prompt for output directory in GUI mode if not specified
        print("\nSelect output directory (or cancel to preserve folder structure next to source files)...")
        output_dir = select_output_directory_gui()
        if output_dir:
            print(f"Output directory: {output_dir}")
        else:
            print("Output will be created next to source files")
    
    # Convert each file
    success_count = 0
    for lua_file in lua_files:
        if not os.path.exists(lua_file):
            print(f"Error: File not found: {lua_file}")
            continue
        
        try:
            print(f"\n{'='*50}")
            print(f"Converting: {lua_file}")
            print(f"{'='*50}")
            
            # Determine output path
            if output_dir:
                lua_path = Path(lua_file)
                
                # If we have a base path, preserve the folder structure
                if input_base_path:
                    # Calculate relative path from base
                    try:
                        rel_path = os.path.relpath(lua_file, input_base_path)
                        # Create output path preserving structure
                        output_path = Path(output_dir) / rel_path
                        output_path = output_path.with_suffix('.json')
                        
                        # Create parent directories if they don't exist
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        output_file = str(output_path)
                    except ValueError:
                        # If relative path fails, just use the filename
                        output_file = os.path.join(output_dir, f"{lua_path.stem}.json")
                else:
                    # No base path, just use filename
                    output_file = os.path.join(output_dir, f"{lua_path.stem}.json")
            else:
                output_file = None  # Will use default (same directory as input)
            
            output_file = convert_lua_to_json(lua_file, output_file)
            print(f"✓ Successfully created: {output_file}")
            success_count += 1
        except Exception as e:
            print(f"✗ Error converting {lua_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"Conversion complete! {success_count}/{len(lua_files)} files converted successfully.")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
