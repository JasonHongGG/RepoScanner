import os


# Valid path relative for execution from root
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
HISTORY_FILE = os.path.join(CACHE_DIR, "scanned_repos.txt")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def load_scanned_ids():
    """Returns a set of scanned repository IDs (as strings)."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        # Read non-empty lines and strip whitespace
        return set(line.strip() for line in f if line.strip())

def mark_as_scanned(repo_id):
    """Appends a repository ID to the history file."""
    if not repo_id:
        return
        
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{repo_id}\n")
