import os
import sys
import json

def convert_to_utf8(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='cp1252') as f:
            content = f.read()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Converted {file_path} to UTF-8")

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                convert_to_utf8(file_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_encoding.py <directory1> <directory2> ...")
        sys.exit(1)

    for directory in sys.argv[1:]:
        process_directory(directory)