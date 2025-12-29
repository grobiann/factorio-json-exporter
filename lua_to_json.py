#!/usr/bin/env python3
"""
Factorio Lua to JSON Exporter
Converts Factorio mod Lua data files to JSON format.
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
import tkinter as tk
from tkinter import filedialog


class LuaTableParser:
    """Parser for Lua table structures in Factorio data files."""
    
    def __init__(self, content: str):
        self.content = content
        self.pos = 0
        self.length = len(content)
    
    def skip_whitespace(self):
        """Skip whitespace and comments."""
        while self.pos < self.length:
            # Skip whitespace
            if self.content[self.pos].isspace():
                self.pos += 1
                continue
            
            # Skip single-line comments
            if self.content[self.pos:self.pos+2] == '--':
                # Find end of line
                while self.pos < self.length and self.content[self.pos] != '\n':
                    self.pos += 1
                continue
            
            # Skip multi-line comments
            if self.content[self.pos:self.pos+4] == '--[[':
                # Find end of comment
                end = self.content.find(']]', self.pos + 4)
                if end != -1:
                    self.pos = end + 2
                else:
                    self.pos = self.length
                continue
            
            break
    
    def peek(self, length: int = 1) -> str:
        """Peek at the next characters without consuming them."""
        self.skip_whitespace()
        return self.content[self.pos:self.pos+length]
    
    def consume(self, expected: Optional[str] = None) -> str:
        """Consume and return the next character."""
        self.skip_whitespace()
        if self.pos >= self.length:
            raise ValueError("Unexpected end of input")
        
        char = self.content[self.pos]
        if expected and char != expected:
            raise ValueError(f"Expected '{expected}' but got '{char}' at position {self.pos}")
        
        self.pos += 1
        return char
    
    def parse_string(self) -> str:
        """Parse a Lua string (single or double quoted)."""
        self.skip_whitespace()
        quote = self.content[self.pos]
        if quote not in ['"', "'"]:
            raise ValueError(f"Expected string quote but got '{quote}'")
        
        self.pos += 1
        start = self.pos
        escaped = False
        
        while self.pos < self.length:
            char = self.content[self.pos]
            if escaped:
                escaped = False
                self.pos += 1
                continue
            
            if char == '\\':
                escaped = True
                self.pos += 1
                continue
            
            if char == quote:
                result = self.content[start:self.pos]
                self.pos += 1
                return result
            
            self.pos += 1
        
        raise ValueError("Unterminated string")
    
    def parse_number(self) -> float:
        """Parse a Lua number."""
        self.skip_whitespace()
        start = self.pos
        
        # Handle negative numbers
        if self.content[self.pos] == '-':
            self.pos += 1
        
        # Parse digits
        while self.pos < self.length and (self.content[self.pos].isdigit() or self.content[self.pos] in '.eE+-'):
            self.pos += 1
        
        num_str = self.content[start:self.pos]
        try:
            if '.' in num_str or 'e' in num_str or 'E' in num_str:
                return float(num_str)
            return int(num_str)
        except ValueError:
            raise ValueError(f"Invalid number: {num_str}")
    
    def parse_identifier(self) -> str:
        """Parse a Lua identifier."""
        self.skip_whitespace()
        start = self.pos
        
        while self.pos < self.length and (self.content[self.pos].isalnum() or self.content[self.pos] in '_-'):
            self.pos += 1
        
        return self.content[start:self.pos]
    
    def parse_value(self) -> Any:
        """Parse a Lua value (string, number, boolean, table, etc.)."""
        self.skip_whitespace()
        
        if self.pos >= self.length:
            return None
        
        # Table
        if self.peek() == '{':
            return self.parse_table()
        
        # String
        if self.peek() in ['"', "'"]:
            return self.parse_string()
        
        # Number
        if self.peek().isdigit() or self.peek() == '-':
            return self.parse_number()
        
        # Boolean or identifier
        identifier = self.parse_identifier()
        if identifier == 'true':
            return True
        elif identifier == 'false':
            return False
        elif identifier == 'nil':
            return None
        else:
            # Return as string for unknown identifiers
            return identifier
    
    def parse_table(self) -> Dict[str, Any] | List[Any]:
        """Parse a Lua table."""
        self.consume('{')
        
        result = {}
        array_items = []
        is_array = True
        index = 1
        
        while True:
            self.skip_whitespace()
            
            # Check for end of table
            if self.peek() == '}':
                self.consume('}')
                break
            
            # Parse key-value pair or array item
            if self.peek() == '[':
                # Explicit key: [key] = value
                self.consume('[')
                key = self.parse_value()
                self.consume(']')
                self.skip_whitespace()
                self.consume('=')
                value = self.parse_value()
                result[str(key)] = value
                is_array = False
            else:
                # Try to parse as key = value
                saved_pos = self.pos
                try:
                    key = self.parse_identifier()
                    self.skip_whitespace()
                    
                    if self.peek() == '=':
                        # It's a key-value pair
                        self.consume('=')
                        value = self.parse_value()
                        result[key] = value
                        is_array = False
                    else:
                        # It's an array item
                        self.pos = saved_pos
                        value = self.parse_value()
                        array_items.append(value)
                        result[str(index)] = value
                        index += 1
                except:
                    # If parsing fails, try as array item
                    self.pos = saved_pos
                    value = self.parse_value()
                    array_items.append(value)
                    result[str(index)] = value
                    index += 1
            
            # Check for comma
            self.skip_whitespace()
            if self.peek() == ',':
                self.consume(',')
            elif self.peek() != '}':
                # Allow missing comma before closing brace
                pass
        
        # Return array if all keys are sequential integers starting from 1
        if is_array and len(array_items) > 0:
            return array_items
        
        return result
    
    def parse(self) -> Any:
        """Parse the entire Lua content."""
        return self.parse_value()


def extract_data_extend(lua_content: str) -> List[Dict[str, Any]]:
    """Extract data:extend() calls from Lua content."""
    items = []
    
    # Find all data:extend({ ... }) patterns
    pattern = r'data:extend\s*\(\s*\{'
    matches = list(re.finditer(pattern, lua_content))
    
    for match in matches:
        # Find the matching closing brace
        start = match.end() - 1  # Position of opening {
        brace_count = 1
        pos = start + 1
        
        while pos < len(lua_content) and brace_count > 0:
            if lua_content[pos] == '{':
                brace_count += 1
            elif lua_content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        # Extract the table content
        table_content = lua_content[start:pos]
        
        try:
            parser = LuaTableParser(table_content)
            parsed = parser.parse()
            
            if isinstance(parsed, list):
                items.extend(parsed)
            elif isinstance(parsed, dict):
                items.append(parsed)
        except Exception as e:
            print(f"Warning: Failed to parse data:extend block: {e}")
            continue
    
    return items


def convert_lua_to_json(lua_file_path: str, output_file_path: Optional[str] = None) -> str:
    """
    Convert a Lua data file to JSON format.
    
    Args:
        lua_file_path: Path to the Lua file to convert
        output_file_path: Optional path for the output JSON file
    
    Returns:
        Path to the created JSON file
    """
    # Read Lua file
    with open(lua_file_path, 'r', encoding='utf-8') as f:
        lua_content = f.read()
    
    # Extract data
    items = extract_data_extend(lua_content)
    
    # Generate output filename if not provided
    if output_file_path is None:
        lua_path = Path(lua_file_path)
        output_file_path = lua_path.parent / f"{lua_path.stem}.json"
    
    # Write JSON file
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
    print("Factorio Lua to JSON Exporter")
    print("=" * 50)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Convert Factorio Lua data files to JSON format",
        epilog="If no files are specified, a GUI file picker will open."
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Lua files to convert'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output directory for JSON files (default: same as input files)'
    )
    
    args = parser.parse_args()
    
    # Get input files
    if args.files:
        lua_files = args.files
    else:
        # Open file selection dialog
        print("Select Lua files to convert...")
        lua_files = select_files_gui()
    
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
    elif not args.files:
        # Only prompt for output directory in GUI mode if not specified
        print("\nSelect output directory (or cancel to use same directory as input files)...")
        output_dir = select_output_directory_gui()
        if output_dir:
            print(f"Output directory: {output_dir}")
        else:
            print("Using same directory as input files")
    
    # Convert each file
    for lua_file in lua_files:
        if not os.path.exists(lua_file):
            print(f"Error: File not found: {lua_file}")
            continue
        
        try:
            print(f"\nConverting: {lua_file}")
            
            # Determine output path
            if output_dir:
                lua_path = Path(lua_file)
                output_file = os.path.join(output_dir, f"{lua_path.stem}.json")
            else:
                output_file = None  # Will use default (same directory as input)
            
            output_file = convert_lua_to_json(lua_file, output_file)
            print(f"✓ Created: {output_file}")
        except Exception as e:
            print(f"✗ Error converting {lua_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nConversion complete!")


if __name__ == "__main__":
    main()
