"""
Utility script to clean up project files and remove temporary files
"""
import os
import shutil
import glob

def cleanup_cache_files():
    """Remove Python cache files and directories"""
    print("Removing Python cache files...")
    
    # Find all __pycache__ directories
    pycache_dirs = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_dirs.append(os.path.join(root, '__pycache__'))
    
    # Remove each pycache directory
    for directory in pycache_dirs:
        try:
            shutil.rmtree(directory)
            print(f"  Removed: {directory}")
        except Exception as e:
            print(f"  Error removing {directory}: {e}")
    
    # Find and remove .pyc files
    pyc_files = glob.glob('**/*.pyc', recursive=True)
    for file in pyc_files:
        try:
            os.remove(file)
            print(f"  Removed: {file}")
        except Exception as e:
            print(f"  Error removing {file}: {e}")
    
    return True

def cleanup_build_artifacts():
    """Remove build artifacts"""
    print("\nRemoving build artifacts...")
    
    # Directories to remove
    build_dirs = [
        'build',
        'dist',
        '*.egg-info',
        '.pytest_cache',
        '.coverage'
    ]
    
    for pattern in build_dirs:
        for directory in glob.glob(pattern, recursive=False):
            try:
                if os.path.isdir(directory):
                    shutil.rmtree(directory)
                else:
                    os.remove(directory)
                print(f"  Removed: {directory}")
            except Exception as e:
                print(f"  Error removing {directory}: {e}")
    
    return True

def cleanup_temporary_files():
    """Remove temporary files"""
    print("\nRemoving temporary files...")
    
    # File patterns to remove
    temp_patterns = [
        '**/*.bak',
        '**/*.tmp',
        '**/*.log',
        '**/.DS_Store'
    ]
    
    for pattern in temp_patterns:
        for file in glob.glob(pattern, recursive=True):
            try:
                os.remove(file)
                print(f"  Removed: {file}")
            except Exception as e:
                print(f"  Error removing {file}: {e}")
    
    return True

def main():
    """Main function"""
    print("===== Project Cleanup Utility =====")
    
    cleanup_cache_files()
    cleanup_build_artifacts()
    cleanup_temporary_files()
    
    print("\nProject cleanup completed.")

if __name__ == "__main__":
    main() 