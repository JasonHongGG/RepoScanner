import git
import os
import shutil
import stat
from datetime import datetime, timezone, timedelta

class RepoProcessor:
    def __init__(self, temp_dir="cache"):
        self.temp_dir = temp_dir
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    if os.name == 'nt':
        @staticmethod
        def remove_readonly(func, path, exc_info):
            # Clear the readonly bit and reattempt the removal
            os.chmod(path, stat.S_IWRITE)
            func(path)
    else:
        remove_readonly = None

    def delete_repo(self, repo_path):
        """
        Safely deletes a repository directory.
        """
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, onerror=self.remove_readonly if os.name == 'nt' else None)
            except Exception as e:
                print(f"Error deleting {repo_path}: {e}")

    def clone_repo(self, repo_url, repo_name):
        """
        Clones a repository to the temp directory.
        Returns the path to the cloned repo or None if failed.
        """
        repo_path = os.path.join(self.temp_dir, repo_name)
        self.delete_repo(repo_path) # Clean up previous run if exists
            
        try:
            print(f"Cloning {repo_url} to {repo_path}...")
            git.Repo.clone_from(repo_url, repo_path, depth=100) # Clone with depth to save time, unless we need full history
            return repo_path
        except Exception as e:
            print(f"Failed to clone {repo_url}: {e}")
            return None

    def scan_history(self, repo_path, depth=10, scanner_func=None, max_file_age_months=None):
        """
        Scans the commit history for secrets.
        scanner_func: Callback function (text) -> matches
        """
        results = []
        try:
            repo = git.Repo(repo_path)
            # Use 'main' or 'master' or 'HEAD'
            commits = list(repo.iter_commits('HEAD', max_count=depth if isinstance(depth, int) else None))
            
            print(f"Scanning {len(commits)} commits...")
            
            # Calculate cutoff date if needed
            cutoff_date = None
            if max_file_age_months and max_file_age_months > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_file_age_months*30)
            
            for commit in commits:
                # Check commit age
                if cutoff_date and commit.committed_datetime < cutoff_date:
                    # If this commit is too old, and we assume commits are ordered, we could break?
                    # But branches/merges might make it non-linear. safely continue or break?
                    # Usually iter_commits is reverse chronological.
                    # Let's break to be efficient, assuming mostly linear history from HEAD.
                    # Or just continue to be safe. Let's continue.
                    continue

                # Scan commit message
                if scanner_func:
                    msg_matches = scanner_func(commit.message)
                    for m in msg_matches:
                        m['commit'] = commit.hexsha
                        m['location'] = "commit_message"
                        results.append(m)

                # Scan diffs (changes in this commit)
                # If it's the first commit, diff against empty tree
                if not commit.parents:
                    # Initial commit - scan all files in tree
                     # This might be heavy, but it's only one commit.
                     pass # TODO: Handle initial commit better?
                else:
                    diffs = commit.diff(commit.parents[0], create_patch=True)
                    for diff in diffs:
                        # We only care about added/modified content
                        # diff.diff contains the patch text (metadata + content)
                        # or we can read the blob if exist
                        text_to_scan = ""
                        
                        # Try to get patch (diff text)
                        try:
                            # Decode bytes to string
                            text_to_scan = diff.diff.decode('utf-8', errors='ignore')
                        except:
                            continue
                            
                        if scanner_func and text_to_scan:
                            matches = scanner_func(text_to_scan)
                            for m in matches:
                                m['commit'] = commit.hexsha
                                m['location'] = f"file_diff: {diff.b_path}"
                                results.append(m)
                                
        except Exception as e:
            print(f"Error scanning history: {e}")
            
        return results

    def scan_current_files(self, repo_path, scanner_func, max_file_age_months=None):
        """
        Scans the current checkout files on disk.
        """
        results = []
        
        cutoff_timestamp = 0
        if max_file_age_months and max_file_age_months > 0:
             # Unix timestamp for cutoff
             cutoff_timestamp = (datetime.now() - timedelta(days=max_file_age_months*30)).timestamp()

        # Initialize repo object once for git commands
        try:
            repo = git.Repo(repo_path)
        except:
            repo = None

        for root, _, files in os.walk(repo_path):
            if ".git" in root:
                continue
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check file age if requested
                if cutoff_timestamp > 0 and repo:
                    try:
                        # Get relative path for git command
                        rel_path = os.path.relpath(file_path, repo_path)
                        # Get last commit timestamp for this file
                        # -1: last commit, --format=%ct: commit time as unix timestamp
                        last_commit_ts = repo.git.log('-1', '--format=%ct', '--', rel_path)
                        if last_commit_ts and int(last_commit_ts) < cutoff_timestamp:
                            continue # Skip old file
                    except Exception as e:
                        # If git fails, maybe just proceed? or skip?
                        # Proceeding is safer to not miss secrets, but adhering to user rule -> skip?
                        # Let's Skip if we can't determine age to be safe? Or include?
                        # Error usually means file is not tracked. If not tracked, it's new/untracked?
                        # scan unwatched files? Let's treat untracked as "new" (keep them).
                        pass

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if scanner_func:
                            matches = scanner_func(content)
                            for m in matches:
                                m['commit'] = "current_head"
                                m['location'] = f"file: {file_path}"
                                results.append(m)
                except Exception:
                    pass # Skip binary or unreadable files
        return results
