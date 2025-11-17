#!/usr/bin/env python3
"""
Script to convert Tu_pono_logo.png to .ico format for Windows executable
"""

from PIL import Image
import os

def create_icon():
    """Convert PNG logo to ICO format with multiple sizes"""
    
    logo_path = "Tu_pono_logo.png"
    icon_path = "Tu_pono_icon.ico"
    
    if not os.path.exists(logo_path):
        print(f"Error: {logo_path} not found!")
        return False
    
    try:
        # Load the original image
        img = Image.open(logo_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create multiple sizes for the icon (Windows standard sizes)
        sizes = [16, 24, 32, 48, 64, 128, 256]
        icon_images = []
        
        for size in sizes:
            # Resize maintaining aspect ratio
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO file with all sizes
        icon_images[0].save(
            icon_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        print(f"✓ Successfully created {icon_path} with {len(sizes)} sizes")
        return True
        
    except Exception as e:
        print(f"Error creating icon: {e}")
        return False

if __name__ == "__main__":
    create_icon()