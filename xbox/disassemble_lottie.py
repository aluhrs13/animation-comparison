#!/usr/bin/env python3
"""
Lottie Animation Splitter

This script reads a Lottie JSON file and outputs multiple Lottie JSON files,
each containing one major part of the animation.
"""

import json
import os
import copy
import argparse
from typing import Dict, List, Any, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_used_assets(obj: Any, all_assets: List[Dict[str, Any]], used_assets: Set[str]) -> None:
    """
    Recursively find all assets used by an object and its children.
    
    Args:
        obj: The object to examine (layer, shape, property, etc.)
        all_assets: List of all assets in the animation
        used_assets: Set to collect asset IDs
    """
    logging.debug(f"Extracting assets from object: {obj}")
    if not isinstance(obj, (dict, list)):
        return
    
    if isinstance(obj, dict):
        # Check for direct asset references
        if 'refId' in obj and isinstance(obj['refId'], str):
            used_assets.add(obj['refId'])
            
            # For precomps, recursively process their layers
            for asset in all_assets:
                if asset.get('id') == obj['refId'] and 'layers' in asset:
                    for sub_layer in asset['layers']:
                        extract_used_assets(sub_layer, all_assets, used_assets)
        
        # Process all properties
        for key, value in obj.items():
            # Skip simple properties that won't contain asset references
            if key in ('nm', 'id', 'p', 'u', 'w', 'h'):
                continue
            extract_used_assets(value, all_assets, used_assets)
    
    elif isinstance(obj, list):
        for item in obj:
            extract_used_assets(item, all_assets, used_assets)

def create_asset_animation(lottie_data: Dict[str, Any], asset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new Lottie animation from an asset.
    
    Args:
        lottie_data: The original Lottie data
        asset: The asset to extract
        
    Returns:
        A new Lottie animation containing the asset
    """
    asset_id = asset.get('id', 'unknown')
    
    # Create a base animation with the same settings as the original
    new_animation = {
        "v": lottie_data.get("v", "5.7.0"),
        "fr": lottie_data.get("fr", 60),
        "ip": lottie_data.get("ip", 0),
        "op": lottie_data.get("op", 60),
        "w": lottie_data.get("w", 512),
        "h": lottie_data.get("h", 512),
        "nm": f"Asset_{asset_id}",
        "ddd": lottie_data.get("ddd", 0),
    }
    
    # Handle composition assets
    if 'layers' in asset:
        # Use the composition's layers
        new_animation['layers'] = copy.deepcopy(asset['layers'])
        
        # Find assets used by this composition
        used_assets = set()
        for layer in asset['layers']:
            extract_used_assets(layer, lottie_data.get('assets', []), used_assets)
        
        # Keep only the assets needed for this composition
        if used_assets:
            new_animation['assets'] = [
                a for a in lottie_data.get('assets', []) 
                if a.get('id') in used_assets
            ]
    elif 'w' in asset and 'h' in asset and 'p' in asset:
        # This is an image asset
        # Create a simple layer that references this image
        new_animation['assets'] = [copy.deepcopy(asset)]
        new_animation['layers'] = [{
            "ddd": 0,
            "ind": 1,
            "ty": 2,  # Image layer
            "nm": f"Image_{asset_id}",
            "refId": asset_id,
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},  # Opacity
                "r": {"a": 0, "k": 0},     # Rotation
                "p": {"a": 0, "k": [new_animation["w"]/2, new_animation["h"]/2, 0]},  # Position
                "a": {"a": 0, "k": [asset.get("w", 0)/2, asset.get("h", 0)/2, 0]},    # Anchor
                "s": {"a": 0, "k": [100, 100, 100]}  # Scale
            },
            "ao": 0,
            "ip": 0,
            "op": new_animation["op"],
            "st": 0,
            "bm": 0
        }]
    
    return new_animation

def extract_layers_from_composition(lottie_data: Dict[str, Any], composition: Dict[str, Any], 
                                   output_dir: str, comp_name: str) -> None:
    """
    Extract individual layers from a composition asset and save them as separate files.
    
    Args:
        lottie_data: The original Lottie data
        composition: The composition asset containing layers
        output_dir: Directory to save the extracted layers
        comp_name: Name of the composition for prefixing filenames
    """
    if 'layers' not in composition:
        logging.warning(f"No layers found in composition {comp_name}")
        return
    
    logging.info(f"Extracting {len(composition['layers'])} layers from composition {comp_name}")
    
    for i, layer in enumerate(composition['layers']):
        layer_name = layer.get('nm', f'unnamed_layer_{i}')
        safe_layer_name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in layer_name)
        output_filename = f"comp_{comp_name}_layer_{safe_layer_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Create a new animation with just this layer
        new_animation = {
            "v": lottie_data.get("v", "5.7.0"),
            "fr": lottie_data.get("fr", 60),
            "ip": lottie_data.get("ip", 0),
            "op": lottie_data.get("op", 60),
            "w": lottie_data.get("w", 512),
            "h": lottie_data.get("h", 512),
            "nm": f"{comp_name}_{layer_name}",
            "ddd": lottie_data.get("ddd", 0),
            "layers": [copy.deepcopy(layer)]
        }
        
        # Find assets used by this layer
        used_assets = set()
        extract_used_assets(layer, lottie_data.get('assets', []), used_assets)
        
        # Keep only the assets needed for this layer
        if used_assets:
            new_animation['assets'] = [
                asset for asset in lottie_data.get('assets', [])
                if asset.get('id') in used_assets
            ]
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_animation, f, indent=2)
        
        logging.info(f"Extracted layer to file: {output_path}")
        
        # If this layer references a precomp, recursively extract its layers
        if layer.get('ty') == 0 and 'refId' in layer:  # Type 0 is precomp
            refId = layer['refId']
            for asset in lottie_data.get('assets', []):
                if asset.get('id') == refId and 'layers' in asset:
                    # Found the referenced precomp, extract its layers
                    nested_comp_name = f"{comp_name}_{safe_layer_name}"
                    extract_layers_from_composition(lottie_data, asset, output_dir, nested_comp_name)
                    break

def extract_and_save_assets(lottie_data: Dict[str, Any], output_dir: str, base_filename: str) -> None:
    """
    Extract assets from a Lottie animation and save them as separate files.
    
    Args:
        lottie_data: The Lottie animation data
        output_dir: Directory to save the extracted assets
        base_filename: Base name for the output files
    """
    assets = lottie_data.get('assets', [])
    if not assets:
        logging.info("No assets found in the Lottie animation.")
        return
    
    logging.info(f"Found {len(assets)} assets to extract.")
    
    for asset in assets:
        asset_id = asset.get('id', 'unknown')
        asset_name = asset.get('nm', asset_id)
        
        # Make a safe filename
        safe_name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in asset_name)
        output_filename = f"asset_{safe_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # For image assets, just log the information
        if 'p' in asset and 'u' in asset:
            logging.info(f"Image asset: {asset_id}, Path: {asset['u']}{asset['p']}, Dimensions: {asset.get('w', 'N/A')}x{asset.get('h', 'N/A')}")
            
            # Create a simple animation with just this image
            new_animation = create_asset_animation(lottie_data, asset)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(new_animation, f, indent=2)
            logging.info(f"Saved image asset animation to: {output_path}")
            
        # For composition assets, create a new Lottie file
        elif 'layers' in asset:
            logging.info(f"Composition asset: {asset_id}, Layers: {len(asset['layers'])}")
            
            # Create a new animation from this asset
            new_animation = create_asset_animation(lottie_data, asset)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(new_animation, f, indent=2)
            logging.info(f"Saved composition asset to: {output_path}")
            
            # Recursively extract individual layers from this composition
            extract_layers_from_composition(lottie_data, asset, output_dir, safe_name)
        else:
            logging.warning(f"Unknown asset type: {asset_id}")

def find_shapes_recursive(obj: Any, path: List[str] = None, shapes: List[Dict] = None) -> List[Dict]:
    """
    Recursively find all shapes in the Lottie data.
    
    Args:
        obj: The object to examine
        path: Current path in the object hierarchy
        shapes: List to collect shapes and their paths
        
    Returns:
        List of dictionaries containing shapes and their metadata
    """
    if path is None:
        path = []
    if shapes is None:
        shapes = []
    
    if not isinstance(obj, (dict, list)):
        return shapes
    
    if isinstance(obj, dict):
        # Check if this is a shape definition
        if 'ty' in obj and obj.get('ty') in ['sh', 'rc', 'el', 'sr', 'st', 'fl', 'gf', 'gs']:
            # Found a shape - save it with its path
            # Shape types: sh (path), rc (rectangle), el (ellipse), sr (star), 
            # st (stroke), fl (fill), gf (gradient fill), gs (gradient stroke)
            shape_name = obj.get('nm', 'unnamed_shape')
            shapes.append({
                'shape': obj,
                'name': shape_name,
                'path': list(path),
                'type': obj.get('ty', 'unknown')
            })
        
        # Also check if this is a shape group (a container for shapes)
        if 'ty' in obj and obj.get('ty') == 'gr' and 'it' in obj:
            # This is a shape group - it can contain multiple shapes
            group_name = obj.get('nm', 'unnamed_group')
            shapes.append({
                'shape': obj,
                'name': group_name,
                'path': list(path),
                'type': 'group'
            })
        
        # Continue recursion
        for key, value in obj.items():
            find_shapes_recursive(value, path + [key], shapes)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_shapes_recursive(item, path + [str(i)], shapes)
    
    return shapes

def create_static_shape_animation(lottie_data: Dict[str, Any], shape_data: Dict) -> Dict[str, Any]:
    """
    Create a new static Lottie animation from a shape.
    
    Args:
        lottie_data: The original Lottie data
        shape_data: The shape data to convert
        
    Returns:
        A new Lottie animation containing just the static shape
    """
    # Create a base animation with the same settings as the original
    new_animation = {
        "v": lottie_data.get("v", "5.7.0"),
        "fr": lottie_data.get("fr", 60),
        "ip": 0,
        "op": 1,  # Just 1 frame for static
        "w": lottie_data.get("w", 512),
        "h": lottie_data.get("h", 512),
        "nm": f"Shape_{shape_data['name']}",
        "ddd": 0,
    }
    
    shape_obj = shape_data['shape']
    
    # Create a shape layer
    if shape_data['type'] == 'group':
        # If it's a shape group, use it directly
        shape_layer = {
            "ddd": 0,
            "ind": 1,
            "ty": 4,  # Shape layer
            "nm": f"Shape_{shape_data['name']}",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},  # Opacity
                "r": {"a": 0, "k": 0},     # Rotation
                "p": {"a": 0, "k": [new_animation["w"]/2, new_animation["h"]/2, 0]},  # Position
                "a": {"a": 0, "k": [0, 0, 0]},    # Anchor
                "s": {"a": 0, "k": [100, 100, 100]}  # Scale
            },
            "ao": 0,
            "shapes": [copy.deepcopy(shape_obj)],
            "ip": 0,
            "op": 1,
            "st": 0,
            "bm": 0
        }
    elif shape_data['type'] in ['sh', 'rc', 'el', 'sr']:
        # Individual shapes need to be wrapped in a shape group
        shape_layer = {
            "ddd": 0,
            "ind": 1,
            "ty": 4,  # Shape layer
            "nm": f"Shape_{shape_data['name']}",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},
                "r": {"a": 0, "k": 0},
                "p": {"a": 0, "k": [new_animation["w"]/2, new_animation["h"]/2, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]}
            },
            "ao": 0,
            "shapes": [{
                "ty": "gr",
                "it": [
                    copy.deepcopy(shape_obj),
                    {
                        "ty": "st",  # Add a simple stroke if none exists
                        "c": {"a": 0, "k": [0, 0, 0, 1]},
                        "o": {"a": 0, "k": 100},
                        "w": {"a": 0, "k": 2},
                        "lc": 2,
                        "lj": 2,
                        "nm": "Stroke"
                    },
                    {
                        "ty": "tr",  # Transform
                        "p": {"a": 0, "k": [0, 0]},
                        "a": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [100, 100]},
                        "r": {"a": 0, "k": 0},
                        "o": {"a": 0, "k": 100},
                        "sk": {"a": 0, "k": 0},
                        "sa": {"a": 0, "k": 0},
                        "nm": "Transform"
                    }
                ],
                "nm": f"Group_{shape_data['name']}"
            }],
            "ip": 0,
            "op": 1,
            "st": 0,
            "bm": 0
        }
    else:
        # For other types (fills, strokes, etc.), we need a complete shape to apply them to
        # Just create a simple rectangle with the style applied
        shape_layer = {
            "ddd": 0,
            "ind": 1,
            "ty": 4,
            "nm": f"Style_{shape_data['name']}",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},
                "r": {"a": 0, "k": 0},
                "p": {"a": 0, "k": [new_animation["w"]/2, new_animation["h"]/2, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]}
            },
            "ao": 0,
            "shapes": [{
                "ty": "gr",
                "it": [
                    {
                        "ty": "rc",  # Rectangle
                        "d": 1,
                        "s": {"a": 0, "k": [100, 100]},
                        "p": {"a": 0, "k": [0, 0]},
                        "r": {"a": 0, "k": 0},
                        "nm": "Rectangle"
                    },
                    copy.deepcopy(shape_obj),  # Apply the style to the rectangle
                    {
                        "ty": "tr",
                        "p": {"a": 0, "k": [0, 0]},
                        "a": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [100, 100]},
                        "r": {"a": 0, "k": 0},
                        "o": {"a": 0, "k": 100},
                        "sk": {"a": 0, "k": 0},
                        "sa": {"a": 0, "k": 0},
                        "nm": "Transform"
                    }
                ],
                "nm": f"Group_{shape_data['name']}"
            }],
            "ip": 0,
            "op": 1,
            "st": 0,
            "bm": 0
        }
    
    new_animation['layers'] = [shape_layer]
    return new_animation

def extract_and_save_shapes(lottie_data: Dict[str, Any], output_dir: str) -> None:
    """
    Extract shapes from a Lottie animation and save them as separate static files.
    
    Args:
        lottie_data: The Lottie animation data
        output_dir: Directory to save the extracted shapes
    """
    # Find all shapes in the Lottie data
    shapes = find_shapes_recursive(lottie_data)
    
    if not shapes:
        logging.info("No shapes found in the Lottie animation.")
        return
    
    logging.info(f"Found {len(shapes)} shapes to extract.")
    
    # Process each shape
    for shape_data in shapes:
        shape_name = shape_data['name']
        
        # Make a safe filename
        safe_name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in shape_name)
        shape_type = shape_data['type']
        output_filename = f"shape_{shape_type}_{safe_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Create a static animation with just this shape
        new_animation = create_static_shape_animation(lottie_data, shape_data)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_animation, f, indent=2)
        
        logging.info(f"Saved static shape to: {output_path}")

def split_lottie_animation(input_file: str, output_dir: str = None) -> None:
    """
    Split a Lottie animation into multiple files.
    
    Args:
        input_file: Path to the input Lottie JSON file
        output_dir: Directory to save the split animations
    """
    # Set default output directory if not provided
    if not output_dir:
        output_dir = os.path.dirname(input_file) or 'split'

    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Delete existing JSON files in the output directory
    for filename in os.listdir(output_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(output_dir, filename)
            try:
                os.remove(file_path)
                logging.info(f"Deleted existing file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete file {file_path}: {e}")
    
    # Read the Lottie animation
    logging.info(f"Reading Lottie animation: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lottie_data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read Lottie file: {e}")
        return
    
    # Check if it has layers
    if 'layers' not in lottie_data:
        logging.error(f"{input_file} doesn't appear to be a valid Lottie animation (no layers found)")
        return
    
    # Get base filename for output
    base_filename = ""
    
    # Process each layer as a separate animation
    for i, layer in enumerate(lottie_data.get('layers', [])):
        logging.info(f"Processing layer {i}: {layer.get('nm', 'Unnamed Layer')}")
        # Skip hidden layers
        if layer.get('hd', False):  # Changed from True to False as hd=True means hidden
            logging.info(f"Skipping hidden layer {i}")
            continue
        
        # Create a new animation with just this layer
        new_animation = copy.deepcopy(lottie_data)
        new_animation['layers'] = [copy.deepcopy(layer)]
        
        # Find assets used by this layer
        used_assets = set()
        #extract_used_assets(layer, lottie_data.get('assets', []), used_assets)
        logging.debug(f"Extracted used assets: {used_assets}")
        
        # Keep only the assets needed for this part
        if 'assets' in new_animation and used_assets:
            new_animation['assets'] = [
                asset for asset in new_animation['assets'] 
                if asset.get('id') in used_assets
            ]
        elif 'assets' in new_animation and not used_assets:
            # No assets needed, remove the assets array
            del new_animation['assets']
        
        # Generate a safe filename
        layer_name = layer.get('nm', f'layer_{i}')
        safe_name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in layer_name)
        output_filename = f"layer_{safe_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_animation, f, indent=2)
        
        logging.info(f"Writing layer {i} to file: {output_path}")
    
    # Extract and save shapes
    extract_and_save_shapes(lottie_data, output_dir)
    
    # Extract and save assets
    #extract_and_save_assets(lottie_data, output_dir, base_filename)
    
    logging.info("Finished splitting Lottie animation.")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Split a Lottie animation into multiple files.')
    parser.add_argument('input_file', help='Path to the input Lottie JSON file')
    parser.add_argument('-o', '--output-dir', help='Directory to save the split animations')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logging.info("Script started.")
    split_lottie_animation(args.input_file, args.output_dir)
    logging.info("Script finished.")

    # Create a summary.json file in the output directory
    summary_path = os.path.join(args.output_dir, "summary.json")
    try:
        files=[]
        for filename in os.listdir(args.output_dir):
            if filename.endswith('.json') and filename != "summary.json":
                files.append(filename)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(files, f, indent=2)
        
        logging.info(f"Created summary file: {summary_path}")
    except Exception as e:
        logging.error(f"Failed to create summary file: {e}")

if __name__ == '__main__':
    main()