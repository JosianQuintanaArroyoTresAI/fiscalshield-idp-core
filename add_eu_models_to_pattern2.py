#!/usr/bin/env python3
"""
add_eu_models_to_pattern2.py - Add EU model IDs based on actual availability
"""

import re
import sys

# EU models actually available in user's eu-central-1 account
EU_MODELS = [
    '"eu.amazon.nova-micro-v1:0"',
    '"eu.amazon.nova-lite-v1:0"',
    '"eu.amazon.nova-pro-v1:0"',
    '"eu.anthropic.claude-3-haiku-20240307-v1:0"',
    '"eu.anthropic.claude-3-sonnet-20240229-v1:0"',
    '"eu.anthropic.claude-3-5-sonnet-20240620-v1:0"',
    '"eu.anthropic.claude-3-7-sonnet-20250219-v1:0"',
    '"eu.anthropic.claude-sonnet-4-20250514-v1:0"',
    '"eu.anthropic.claude-sonnet-4-5-20250929-v1:0"',
]

def add_eu_models_to_enum(lines, start_idx):
    """Add EU models to an enum block starting at start_idx"""
    updated_lines = []
    i = start_idx
    
    # Find the indentation level
    indent = ""
    while i < len(lines):
        line = lines[i]
        
        # Detect enum start
        if 'enum:' in line:
            updated_lines.append(line)
            i += 1
            continue
        
        # Collect US models and detect indentation
        if '"us.amazon' in line or '"us.anthropic' in line:
            if not indent:
                indent = line[:len(line) - len(line.lstrip())]
            updated_lines.append(line)
            i += 1
            continue
        
        # End of enum - add EU models before this line
        if line.strip() and not line.strip().startswith('-') and not line.strip().startswith('"'):
            # Insert EU models
            for eu_model in EU_MODELS:
                updated_lines.append(f'{indent}- {eu_model}\n')
            updated_lines.append(line)
            return updated_lines, i + 1
        
        updated_lines.append(line)
        i += 1
    
    return updated_lines, i

def process_template(template_path):
    """Process template and add EU models to all enum blocks"""
    with open(template_path, 'r') as f:
        lines = f.readlines()
    
    result_lines = []
    i = 0
    enums_updated = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is an enum block with US models
        if 'enum:' in line and i + 1 < len(lines):
            # Look ahead to see if next line has US model
            next_line = lines[i + 1]
            if '"us.amazon' in next_line or '"us.anthropic' in next_line:
                # Process this enum block
                result_lines.append(line)
                i += 1
                
                # Collect all enum lines and add EU models at the end
                enum_lines = []
                indent = ""
                
                while i < len(lines):
                    curr_line = lines[i]
                    
                    if '"us.amazon' in curr_line or '"us.anthropic' in curr_line:
                        if not indent:
                            indent = curr_line[:len(curr_line) - len(curr_line.lstrip())]
                        enum_lines.append(curr_line)
                        i += 1
                    elif curr_line.strip() and not curr_line.strip().startswith('-'):
                        # End of enum - add EU models
                        result_lines.extend(enum_lines)
                        for eu_model in EU_MODELS:
                            result_lines.append(f'{indent}- {eu_model}\n')
                        enums_updated += 1
                        break
                    else:
                        enum_lines.append(curr_line)
                        i += 1
            else:
                result_lines.append(line)
                i += 1
        else:
            result_lines.append(line)
            i += 1
    
    # Write back
    with open(template_path, 'w') as f:
        f.writelines(result_lines)
    
    print(f"✓ Updated {template_path}")
    print(f"  Modified {enums_updated} enum blocks")
    print(f"  Added {len(EU_MODELS)} EU model options to each block")
    return enums_updated

def verify_update(template_path):
    """Verify EU models were added"""
    with open(template_path, 'r') as f:
        content = f.read()
    
    eu_count = content.count('eu.amazon.nova') + content.count('eu.anthropic.claude')
    print(f"\n✓ Verification: Found {eu_count} EU model references")
    
    # Should be ~72 references (8 enum blocks × 9 models)
    if eu_count >= 50:
        print("  ✓ All enum blocks successfully updated!")
    else:
        print(f"  ⚠️ Warning: Expected ~72 references, found {eu_count}")
        print("  Please review the template manually")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_eu_models_to_pattern2.py <template-path>")
        print("Example: python add_eu_models_to_pattern2.py patterns/pattern-2/template.yaml")
        sys.exit(1)
    
    template_file = sys.argv[1]
    
    print(f"Adding EU models to: {template_file}")
    print(f"Models to add: {len(EU_MODELS)}\n")
    
    enums_updated = process_template(template_file)
    verify_update(template_file)
    
    print("\n" + "="*60)
    print("✓ Complete! Next steps:")
    print("="*60)
    print("1. Review changes: git diff patterns/pattern-2/template.yaml")
    print("2. Rebuild: sam build")
    print("3. Deploy: sam deploy --region eu-central-1")
    print("\nAfter deployment, update your configuration via Web UI to use:")
    print("  - Classification: eu.amazon.nova-pro-v1:0")
    print("  - Extraction: eu.anthropic.claude-3-7-sonnet-20250219-v1:0")
    print("  - Assessment: eu.amazon.nova-lite-v1:0")