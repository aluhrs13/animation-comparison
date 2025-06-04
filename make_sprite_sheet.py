#!/usr/bin/env python3
"""
Sprite Sheet Generator
Creates a sprite sheet from individual PNG frames in the assets/PNG/Light/Combined folder.
"""

import os
import math
from PIL import Image


def create_sprite_sheet(input_folder, output_path, cols=None, rows=None):
    """
    Create a sprite sheet from PNG images in the input folder.
    
    Args:
        input_folder (str): Path to folder containing PNG images
        output_path (str): Path for the output sprite sheet
        cols (int, optional): Number of columns. If None, calculates automatically
        rows (int, optional): Number of rows. If None, calculates automatically
    """
    # Get all PNG files and sort them
    png_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.png')]
    png_files.sort()
    
    if not png_files:
        print(f"No PNG files found in {input_folder}")
        return
    
    print(f"Found {len(png_files)} PNG files")
    
    # Load the first image to get dimensions
    first_img_path = os.path.join(input_folder, png_files[0])
    with Image.open(first_img_path) as first_img:
        frame_width, frame_height = first_img.size
    
    print(f"Frame size: {frame_width}x{frame_height}")
    
    # Calculate grid dimensions
    total_frames = len(png_files)
    
    if cols is None and rows is None:
        # Calculate optimal grid (roughly square)
        cols = math.ceil(math.sqrt(total_frames))
        rows = math.ceil(total_frames / cols)
    elif cols is None:
        cols = math.ceil(total_frames / rows)
    elif rows is None:
        rows = math.ceil(total_frames / cols)
    
    print(f"Grid: {cols} columns x {rows} rows")
    
    # Create the sprite sheet
    sprite_width = cols * frame_width
    sprite_height = rows * frame_height
    sprite_sheet = Image.new('RGBA', (sprite_width, sprite_height), (0, 0, 0, 0))
    
    print(f"Sprite sheet size: {sprite_width}x{sprite_height}")
    
    # Paste each frame into the sprite sheet
    for i, filename in enumerate(png_files):
        if i >= cols * rows:
            break
            
        img_path = os.path.join(input_folder, filename)
        
        try:
            with Image.open(img_path) as img:
                # Calculate position in the grid
                col = i % cols
                row = i // cols
                x = col * frame_width
                y = row * frame_height
                
                # Paste the image
                sprite_sheet.paste(img, (x, y))
                
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{total_frames} frames")
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    # Save the sprite sheet
    print(f"Saving sprite sheet to {output_path}")
    sprite_sheet.save(output_path, 'PNG', optimize=True)
    print("Done!")
    
    # Print CSS helper info
    print("\n--- CSS Helper Information ---")
    print(f"Background image size: {sprite_width}px {sprite_height}px")
    print(f"Frame size: {frame_width}px {frame_height}px")
    print(f"Total frames: {total_frames}")
    print(f"Grid: {cols} columns x {rows} rows")
    print("\nExample CSS for animation:")
    print(f".sprite-animation {{")
    print(f"  width: {frame_width}px;")
    print(f"  height: {frame_height}px;")
    print(f"  background-image: url('sprite-sheet.png');")
    print(f"  background-size: {sprite_width}px {sprite_height}px;")
    print(f"  animation: sprite-anim 2s steps({total_frames}) infinite;")
    print(f"}}")
    print(f"\n@keyframes sprite-anim {{")
    print(f"  from {{ background-position: 0 0; }}")
    print(f"  to {{ background-position: -{sprite_width}px 0; }}")
    print(f"}}")


def main():
    """Main function to create sprite sheet from PNG animation frames."""
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, 'assets', 'PNG', 'Light', 'Combined')
    output_path = os.path.join(script_dir, 'sprite-sheet-light.png')
    
    # Check if input folder exists
    if not os.path.exists(input_folder):
        print(f"Input folder not found: {input_folder}")
        return
    
    print(f"Input folder: {input_folder}")
    print(f"Output file: {output_path}")
    
    # Create sprite sheet
    create_sprite_sheet(input_folder, output_path)


if __name__ == "__main__":
    main()