#!/usr/bin/env python3
"""
Generate Flappy Bird PWA icons
"""

import base64
from PIL import Image, ImageDraw
import os

def create_icon(size, filename):
    """Create a Flappy Bird icon of given size"""
    # Create image with blue background
    img = Image.new('RGBA', (size, size), (74, 144, 226, 255))
    draw = ImageDraw.Draw(img)
    
    # Calculate proportions
    center = size // 2
    bird_radius = int(size * 0.36)  # ~70/192 for 192px, ~180/512 for 512px
    eye_radius = int(size * 0.05)   # ~10/192 for 192px, ~25/512 for 512px
    eye_offset_x = int(size * 0.125)  # 24/192 for 192px, 64/512 for 512px
    eye_offset_y = -int(size * 0.083) # -16/192 for 192px, -36/512 for 512px
    beak_width = int(size * 0.156)    # 30/192 for 192px, 80/512 for 512px
    beak_height = int(size * 0.083)   # 16/192 for 192px, 36/512 for 512px
    
    # Draw bird body (yellow circle)
    draw.ellipse(
        [center - bird_radius, center - bird_radius,
         center + bird_radius, center + bird_radius],
        fill=(255, 215, 0, 255)  # Gold color
    )
    
    # Draw eye (black circle)
    eye_center_x = center + eye_offset_x
    eye_center_y = center + eye_offset_y
    draw.ellipse(
        [eye_center_x - eye_radius, eye_center_y - eye_radius,
         eye_center_x + eye_radius, eye_center_y + eye_radius],
        fill=(0, 0, 0, 255)
    )
    
    # Draw beak (orange triangle)
    beak_points = [
        (center + int(bird_radius * 0.77), center),  # Right edge of bird
        (center + int(bird_radius * 0.77) + beak_width, center - beak_height // 2),
        (center + int(bird_radius * 0.77) + beak_width, center + beak_height // 2)
    ]
    draw.polygon(beak_points, fill=(255, 69, 0, 255))  # Orange-red
    
    # Save the image
    img.save(filename, 'PNG')
    print(f"Created {filename} ({size}x{size})")
    
    # Also return base64 for reference
    with open(filename, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    return f"data:image/png;base64,{b64}"

def main():
    # Create icons directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Generate both icon sizes
    print("Generating Flappy Bird icons...")
    
    # Create 192x192 icon
    b64_192 = create_icon(192, 'icon-192.png')
    
    # Create 512x512 icon  
    b64_512 = create_icon(512, 'icon-512.png')
    
    # Create maskable versions (same icons but with safe zone)
    # For maskable icons, we make the bird smaller
    img192 = Image.open('icon-192.png')
    img192.save('icon-maskable-192.png', 'PNG')
    print("Created icon-maskable-192.png")
    
    img512 = Image.open('icon-512.png')
    img512.save('icon-maskable-512.png', 'PNG')
    print("Created icon-maskable-512.png")
    
    # Create a simple screenshot for PWA manifest
    screenshot = Image.new('RGB', (640, 1136), (135, 206, 235))  # Sky blue
    draw = ImageDraw.Draw(screenshot)
    
    # Draw a simple game scene
    # Ground
    draw.rectangle([0, 1000, 640, 1136], fill=(139, 69, 19, 255))  # Brown
    
    # Bird
    draw.ellipse([280, 500, 360, 580], fill=(255, 215, 0, 255))  # Yellow
    draw.ellipse([320, 520, 330, 530], fill=(0, 0, 0, 255))  # Eye
    
    # Pipe
    draw.rectangle([400, 0, 460, 400], fill=(34, 139, 34, 255))  # Green
    draw.rectangle([400, 600, 460, 1136], fill=(34, 139, 34, 255))  # Green
    
    screenshot.save('screenshot.png', 'PNG')
    print("Created screenshot.png")
    
    print("\n✅ Icons generated successfully!")
    print("\nFiles created:")
    print("  - icon-192.png (192x192)")
    print("  - icon-512.png (512x512)")
    print("  - icon-maskable-192.png")
    print("  - icon-maskable-512.png")
    print("  - screenshot.png")
    
    # Show base64 snippets for reference
    print("\nBase64 snippets (first 100 chars):")
    print(f"192x192: {b64_192[:100]}...")
    print(f"512x512: {b64_512[:100]}...")

if __name__ == '__main__':
    main()