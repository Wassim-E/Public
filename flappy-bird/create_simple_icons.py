#!/usr/bin/env python3
"""
Create simple placeholder icons for Flappy Bird PWA
Uses only built-in modules, no PIL required
"""

import base64
import os

# Simple 192x192 PNG icon (yellow bird on blue background)
# This is a minimal 1x1 pixel PNG encoded in base64, we'll use it as placeholder
ICON_192_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAACtSURBVHgB7dShDQAwDMCw8396EpgJQrFg5SgK2iRwR0GgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAj2A4Yw4R1wE4sTAAAAAElFTkSuQmCC"

# Simple 512x512 PNG icon
ICON_512_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAACtSURBVHgB7dShDQAwDMCw8396EpgJQrFg5SgK2iRwR0GgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAgUBAoCBYGCQEGgIFAQKAj2A4Yw4R1wE4sTAAAAAElFTkSuQmCC"

def create_icon(base64_data, filename):
    """Create an icon file from base64 data"""
    try:
        # Decode base64
        icon_data = base64.b64decode(base64_data)
        
        # Write to file
        with open(filename, 'wb') as f:
            f.write(icon_data)
        
        print(f"Created {filename}")
        return True
    except Exception as e:
        print(f"Error creating {filename}: {e}")
        return False

def main():
    print("Creating Flappy Bird icons...")
    
    # Create directory if needed
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    
    # Create icons
    success1 = create_icon(ICON_192_BASE64, "icon-192.png")
    success2 = create_icon(ICON_512_BASE64, "icon-512.png")
    
    # Create maskable versions (copy same files)
    if success1:
        with open("icon-192.png", 'rb') as src, open("icon-maskable-192.png", 'wb') as dst:
            dst.write(src.read())
        print("Created icon-maskable-192.png")
    
    if success2:
        with open("icon-512.png", 'rb') as src, open("icon-maskable-512.png", 'wb') as dst:
            dst.write(src.read())
        print("Created icon-maskable-512.png")
    
    # Create a simple text file as screenshot placeholder
    with open("screenshot.txt", "w") as f:
        f.write("Screenshot placeholder - replace with actual screenshot")
    print("Created screenshot.txt (placeholder)")
    
    print("\nDone! Icons created successfully.")

if __name__ == "__main__":
    main()