import logging
import os
from datetime import datetime, timedelta
from config import PATTERNS, GITHUB_TOKEN
from scanner.github_client import GitHubClient
from scanner.repo_processor import RepoProcessor
from scanner.pattern_matcher import PatternMatcher
from utils.result_writer import ResultWriter
from utils.history import load_scanned_ids, mark_as_scanned

class ScannerEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = GitHubClient(GITHUB_TOKEN)
        self.repo_processor = RepoProcessor()
        self.matcher = PatternMatcher(PATTERNS)
        self.result_writer = ResultWriter()

    def run(self, args):
        self.logger.info("Starting GitHub Secret Scanner Engine...")
        
        if not GITHUB_TOKEN or "your_github_pat" in GITHUB_TOKEN:
            self.logger.warning("GITHUB_TOKEN not found or invalid in .env. Search might be rate-limited.")

        # Setup Results File
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        results_dir = "results"
        extension = "json" if self.result_writer.output_format == "json" else "csv"
        results_file = os.path.join(results_dir, f"scan_results_{timestamp}.{extension}")
        self.logger.info(f"Results will be saved to: {results_file}")

        # Get Repositories
        repos = self._get_repositories(args)
        
        if not repos:
            self.logger.error("No repositories found via search.")
            return

        self.logger.info(f"Found {len(repos)} repositories. Starting scan...")
        
        total_findings = 0
        
        for i, repo in enumerate(repos):
            repo_name = repo.get('name', 'unknown')
            repo_full_name = repo.get('full_name', 'unknown')
            repo_url = repo.get('clone_url', '')
            html_url = repo.get('html_url', '')
            repo_id = str(repo.get('id', ''))
            
            self.logger.info(f"[{i+1}/{len(repos)}] Processing: {repo_full_name} ({repo_url})")
            
            local_path = self.repo_processor.clone_repo(repo_url, repo_name)
            if not local_path:
                self.logger.error(f"Skipping {repo_full_name} due to clone failure.")
                continue
                
            repo_findings = []
            if args.mode == 'history':
                self.logger.info(f"Scanning history (depth={args.depth}, max_file_age={args.file_age}m)...")
                repo_findings = self.repo_processor.scan_history(local_path, depth=args.depth, scanner_func=self.matcher.scan_text, max_file_age_months=args.file_age)
            else:
                self.logger.info(f"Scanning current files (max_file_age={args.file_age}m)...")
                repo_findings = self.repo_processor.scan_current_files(local_path, scanner_func=self.matcher.scan_text, max_file_age_months=args.file_age)
                
            # Post-process findings
            self._enrich_findings(repo_findings, html_url, local_path)
                    
            if repo_findings:
                self.logger.warning(f"FOUND {len(repo_findings)} SECRETS in {repo_full_name}!")
                self.result_writer.save(repo_findings, results_file)
                total_findings += len(repo_findings)
            else:
                self.logger.info(f"No secrets found in {repo_full_name}.")
            
            # Mark as scanned
            if repo_id and repo_id != "manual":
                mark_as_scanned(repo_id)
                
            # Cleanup
            self.repo_processor.delete_repo(local_path)
        
        self.logger.info(f"Scan complete. Total findings: {total_findings}. Results saved to {results_file}")

    def _get_repositories(self, args):
        if args.repo:
            self.logger.info(f"Scanning specific repository: {args.repo}")
            repo_name = args.repo.rstrip('/').split('/')[-1].replace('.git', '')
            return [{
                "id": "manual",
                "name": repo_name,
                "full_name": repo_name,
                "clone_url": args.repo,
                "html_url": args.repo.replace('.git', '')
            }]
        else:
            # Load history
            scanned_ids = load_scanned_ids()
            self.logger.info(f"Loaded {len(scanned_ids)} previously scanned repositories.")
            
            min_created = None
            if args.repo_age > 0:
                date_threshold = datetime.now() - timedelta(days=args.repo_age * 30)
                min_created = date_threshold.strftime("%Y-%m-%d")
                self.logger.info(f"Filtering repos created after: {min_created}")
            
            self.logger.info(f"Searching for {args.count} random repositories (Max Stars: {args.max_stars})...")
            return self.client.search_repositories(max_stars=args.max_stars, limit=args.count, exclude_ids=scanned_ids, min_created_date=min_created)

    def _enrich_findings(self, findings, html_url, local_path):
        for f in findings:
            f['repo'] = html_url
            if 'file_diff: ' in f.get('location', ''):
                path = f['location'].replace('file_diff: ', '')
                f['file_url'] = f"{html_url}/blob/{f['commit']}/{path}"
            elif 'file: ' in f.get('location', ''):
                rel_path = f['location'].replace('file: ', '').replace(local_path, '').replace('\\', '/').lstrip('/')
                f['file_url'] = f"{html_url}/blob/HEAD/{rel_path}"
            else:
                f['file_url'] = "N/A"
