# GitHub Secret Scanner Walkthrough

The GitHub Secret Scanner is now installed and ready to use. This tool randomly scans GitHub repositories for secrets like API keys and passwords.

## Setup

1.  **Configure GitHub Token**:
    Open the `.env` file in `c:\Users\JasonHong\Desktop\CODE\_Project\GithubScanner\.env` and replace `your_github_pat_here` with your actual GitHub Personal Access Token.
    ```env
    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
    ```
    *This is required to avoid strict API rate limits.*

2.  **Dependencies**:
    Ensure dependencies are installed (already done):
    ```powershell
    pip install -r requirements.txt
    ```

## Usage

Run the scanner from the project directory:

```powershell
python main.py [arguments]
```

### Arguments
- `--repo URL`: Scan a specific repository URL (bypasses random search).
- `--count N`: Number of repositories to scan (default: 5).
- `--max-stars N`: Max stars for repositories (default: 10).
- `--mode {current,history}`: Scan mode.
    - `current`: Scans only the current state of files.
    - `history`: Scans the commit history (requires cloning).
- `--depth N`: Number of commits to scan in history mode (default: 10).

### Examples

**Run a small test scan (current files only):**
```powershell
python main.py --count 3 --max-stars 5 --mode current
```

**Run a history scan on 10 repos, checking last 20 commits:**
```powershell
python main.py --count 10 --mode history --depth 20
```

**Scan a specific repository:**
```powershell
python main.py --repo https://github.com/octocat/Hello-World.git --mode history
```

**Run a scan on 10 repos, checking last 20 commits, with max stars of 200, repo age of 12 months, and file age of 6 months:**
``` powershell
python main.py --count 10 --max-stars 200 --mode current --repo-age 12 --file-age 6
```

## Results

- **Console Output**: Shows progress and findings in real-time.
- **Log File**: Detailed logs are saved in `logs/`.
- **CSV Report**: Findings are saved to `scan_results.csv` with columns: `repo`, `type`, `value`, `commit`, `location`, `file_url`.  


> [!CAUTION]
> **Ethical Notice**: If you find valid secrets, please notify the repository owner responsibly. Do not exploit leaked credentials.
