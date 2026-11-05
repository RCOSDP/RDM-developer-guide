#!/usr/bin/env python3
"""
manifest_check.py - Validate manifest/upstreams.json and check TOON consistency

Validates that:
  - Every SHA is 40 hex characters
  - No string contains "http://" or "https://github.com/" pointing to repos ending in -private or -dev2027
  - Every component has id, role, integration_repo, and upstreams fields
  - manifest/upstreams.toon component IDs and SHAs match the JSON

Exit code 0 if all checks pass, 1 if any fail.
"""

import sys
import json
import re
from pathlib import Path


def load_json(path: str) -> dict:
    """Load JSON file and return its contents"""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_toon(path: str) -> dict:
    """Load TOON file and return its contents as a simplified structure"""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    content = filepath.read_text(encoding='utf-8')
    
    # Parse TOON format (simple extraction of component IDs and SHAs)
    components = []
    
    # Match component blocks like:
    # components[4]... or components[]:
    in_components = False
    current_component = {}
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        # Detect start of components section
        if 'components[' in stripped or stripped == 'components[]:':
            in_components = True
            continue
        
        if not in_components:
            continue
        
        # Detect end of components (next top-level section)
        if stripped and not line.startswith(' ') and not line.startswith('\t'):
            if current_component:
                components.append(current_component)
                current_component = {}
            in_components = False
            continue
        
        # Extract component fields
        if stripped.startswith('- id:'):
            if current_component:
                components.append(current_component)
            current_component = {'id': stripped.split(':', 1)[1].strip()}
        elif 'integration_repo:' in stripped and not stripped.startswith(' ') and current_component:
            value = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            current_component['integration_repo'] = value
        elif 'upstreams' in stripped:
            # Extract SHA from upstreams lines
            sha_match = re.search(r'[0-9a-f]{40}', stripped)
            if sha_match and 'upstreams' in current_component:
                current_component.setdefault('shas', []).append(sha_match.group())
    
    if current_component:
        components.append(current_component)
    
    return {'components': components}


def validate_sha(sha: str, field_path: str) -> list[str]:
    """Validate that SHA is 40 hex characters"""
    errors = []
    
    if not isinstance(sha, str):
        errors.append(f"{field_path}: SHA is not a string (got {type(sha).__name__})")
        return errors
    
    if len(sha) != 40:
        errors.append(f"{field_path}: SHA must be exactly 40 characters (got {len(sha)})")
        return errors
    
    if not re.match(r'^[0-9a-f]+$', sha):
        errors.append(f"{field_path}: SHA must be lowercase hex characters only")
    
    return errors


def validate_no_secrets(content: str, filepath: str) -> list[str]:
    """Check that no secrets or GitHub URLs are present"""
    errors = []
    
    # Check for http:// or https://github.com/ pointing to -private or -dev2027
    pattern = r'https?://github\.com/[^"\'\s>]+(?:-private|-dev2027)'
    
    for match in re.finditer(pattern, content):
        line_num = content[:match.start()].count('\n') + 1
        errors.append(f"{filepath} line {line_num}: Found GitHub URL to private/dev2027 repo: {match.group()}")
    
    # Also check for http:// anywhere
    if 'http://' in content:
        for i, line in enumerate(content.split('\n'), 1):
            if 'http://' in line:
                errors.append(f"{filepath} line {i}: Found http:// (should use https): {line.strip()}")
    
    return errors


def validate_component(component: dict, index: int) -> list[str]:
    """Validate a single component has required fields"""
    errors = []
    comp_id = component.get('id', f'component[{index}]')
    
    required_fields = ['id', 'role', 'integration_repo', 'upstreams']
    
    for field in required_fields:
        if field not in component:
            errors.append(f"Component '{comp_id}': Missing required field: {field}")
    
    # Validate SHA in upstreams
    if 'upstreams' in component:
        for i, upstream in enumerate(component['upstreams']):
            if 'sha' in upstream:
                errors.extend(validate_sha(upstream['sha'], f"component '{comp_id}' upstream[{i}].sha"))
    
    # Validate integration_repo format
    if 'integration_repo' in component and component['integration_repo'] is not None:
        repo = component['integration_repo']
        if not re.match(r'^RDM-[A-Za-z0-9_.-]+-dev2027$', repo):
            errors.append(f"Component '{comp_id}': integration_repo must match ^RDM-[A-Za-z0-9_.-]+-dev2027$ (got: {repo})")
    
    return errors


def validate_manifest(json_path: str) -> list[str]:
    """Validate the JSON manifest"""
    errors = []
    
    try:
        data = load_json(json_path)
    except Exception as e:
        return [f"Failed to load {json_path}: {e}"]
    
    # Validate schema_version
    if 'schema_version' not in data:
        errors.append(f"{json_path}: Missing schema_version")
    elif not isinstance(data['schema_version'], int):
        errors.append(f"{json_path}: schema_version must be an integer")
    
    # Validate components
    if 'components' not in data:
        errors.append(f"{json_path}: Missing components")
        return errors
    
    if not isinstance(data['components'], list):
        errors.append(f"{json_path}: components must be an array")
        return errors
    
    component_ids = set()
    
    for i, component in enumerate(data['components']):
        # Check unique IDs
        comp_id = component.get('id')
        if comp_id is None:
            errors.append(f"{json_path} components[{i}]: Missing id field")
        elif comp_id in component_ids:
            errors.append(f"{json_path} components[{i}]: Duplicate component id: {comp_id}")
        else:
            component_ids.add(comp_id)
        
        # Validate component structure
        errors.extend(validate_component(component, i))
    
    return errors


def validate_toon(toon_path: str) -> list[str]:
    """Validate the TOON excerpt"""
    errors = []
    
    try:
        data = load_toon(toon_path)
    except Exception as e:
        return [f"Failed to load {toon_path}: {e}"]
    
    # Check that components exist
    if 'components' not in data or not isinstance(data['components'], list):
        errors.append(f"{toon_path}: Missing components array")
    
    return errors


def main():
    """Main entry point"""
    # Check if we're in the right directory
    manifest_path = Path("manifest/upstreams.json")
    toon_path = Path("manifest/upstreams.toon")
    
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found. This script must be run from the repository root.", file=sys.stderr)
        sys.exit(1)
    
    all_errors = []
    
    # Load JSON manifest
    try:
        json_data = load_json(str(manifest_path))
        content_str = json.dumps(json_data, indent=2)
    except Exception as e:
        print(f"Error loading {manifest_path}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate JSON manifest
    all_errors.extend(validate_manifest(str(manifest_path)))
    
    # Check for secrets in JSON
    all_errors.extend(validate_no_secrets(content_str, str(manifest_path)))
    
    # Load TOON if it exists
    if toon_path.exists():
        try:
            content_toon = toon_path.read_text(encoding='utf-8')
            all_errors.extend(validate_no_secrets(content_toon, str(toon_path)))
        except Exception as e:
            print(f"Warning: Could not load {toon_path}: {e}", file=sys.stderr)
    
    # Print report
    print("=" * 70)
    print("manifest_check.py - Upstream Manifest Validation")
    print("=" * 70)
    
    if all_errors:
        print(f"\nFound {len(all_errors)} error(s):\n")
        for error in all_errors:
            print(f"  • {error}")
        
        print("\n" + "=" * 70)
        print(f"FAILED: {len(all_errors)} error(s) found")
        print("=" * 70)
        sys.exit(1)
    else:
        print(f"\nManifest validation passed.")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
