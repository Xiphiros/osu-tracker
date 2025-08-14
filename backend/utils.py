import os

def get_safe_join(base_dir, *paths):
    """
    Safely joins path components to a base directory and ensures the
    resulting path is a child of the base directory. Returns the absolute,
    safe path or None if the path is invalid.
    """
    if not base_dir or not all(paths):
        return None

    try:
        combined_path = os.path.join(base_dir, *paths)
        abs_base = os.path.abspath(base_dir)
        abs_combined = os.path.abspath(combined_path)

        # Ensure the resolved path is inside the base directory
        if abs_combined.startswith(abs_base):
            return abs_combined
            
    except (TypeError, ValueError):
        # Invalid characters in path components will raise an error
        pass
        
    return None