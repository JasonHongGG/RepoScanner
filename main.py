import logging
import argparse
from config import PATTERNS
from utils.logger import setup_logger

import csv
import sys
import os
import json
from scanner.github_client import GitHubClient
from scanner.repo_processor import RepoProcessor
from scanner.pattern_matcher import PatternMatcher
from config import PATTERNS, GITHUB_TOKEN, OUTPUT_FORMAT
from utils.history import load_scanned_ids, mark_as_scanned

from datetime import datetime, timedelta

def save_results(results, filename):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["repo", "type", "value", "commit", "location", "file_url"], extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        
        for r in results:
            writer.writerow(r)

def save_results_json(results, filename):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    current_data = []
    if os.path.isfile(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except json.JSONDecodeError:
            pass # Start fresh if corrupt
            
    current_data.extend(results)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, indent=4, ensure_ascii=False)

def main():
    logger = setup_logger()
    logger.info("Starting GitHub Secret Scanner...")
    
    parser = argparse.ArgumentParser(description="GitHub Secret Scanner")
    parser.add_argument("--mode", choices=["current", "history"], default="current", help="Scan mode")
    parser.add_argument("--depth", type=int, default=10, help="Commit depth for history scan")
    parser.add_argument("--count", type=int, default=5, help="Number of repositories to scan")
    parser.add_argument("--max-stars", type=int, default=10, help="Max stars for target repos")
    parser.add_argument("--repo-age", type=int, default=0, help="Repo age in months (0=any)")
    parser.add_argument("--file-age", type=int, default=0, help="File age in months (0=any)")
    parser.add_argument("--repo", type=str, help="Specific repository URL to scan (bypasses random search)")
    
    args = parser.parse_args()
    
    # Setup Results File
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = "results"
    
    extension = "json" if OUTPUT_FORMAT == "json" else "csv"
    results_file = os.path.join(results_dir, f"scan_results_{timestamp}.{extension}")
    
    logger.info(f"Results will be saved to: {results_file}")
    
    if not GITHUB_TOKEN or "your_github_pat" in GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not found or invalid in .env. Search might be rate-limited.")
        # Proceed anyway? Or stop? 
        # For now, warn but proceed.
    
    # Initialize
    client = GitHubClient(GITHUB_TOKEN)
    repo_processor = RepoProcessor()
    matcher = PatternMatcher(PATTERNS)
    
    if args.repo:
        logger.info(f"Scanning specific repository: {args.repo}")
        # Construct a mock repo object
        repo_name = args.repo.rstrip('/').split('/')[-1].replace('.git', '')
        repos = [{
            "id": "manual", # No real ID for manual, or fetch it? Doesn't matter for manual mode.
            "name": repo_name,
            "full_name": repo_name, # or user/repo ?
            "clone_url": args.repo,
            "html_url": args.repo.replace('.git', '')
        }]
    else:
        # Load history
        scanned_ids = load_scanned_ids()
        logger.info(f"Loaded {len(scanned_ids)} previously scanned repositories.")
        
        min_created = None
        if args.repo_age > 0:
            date_threshold = datetime.now() - timedelta(days=args.repo_age * 30)
            min_created = date_threshold.strftime("%Y-%m-%d")
            logger.info(f"Filtering repos created after: {min_created}")
        
        logger.info(f"Searching for {args.count} random repositories (Max Stars: {args.max_stars})...")
        repos = client.search_repositories(max_stars=args.max_stars, limit=args.count, exclude_ids=scanned_ids, min_created_date=min_created)
    
    if not repos:
        logger.error("No repositories found via search.")
        return

    logger.info(f"Found {len(repos)} repositories. Starting scan...")
    
    total_findings = 0
    
    for i, repo in enumerate(repos):
        repo_name = repo.get('name', 'unknown')
        repo_full_name = repo.get('full_name', 'unknown')
        repo_url = repo.get('clone_url', '')
        html_url = repo.get('html_url', '')
        repo_id = str(repo.get('id', ''))
        
        logger.info(f"[{i+1}/{len(repos)}] Processing: {repo_full_name} ({repo_url})")
        
        local_path = repo_processor.clone_repo(repo_url, repo_name)
        if not local_path:
            logger.error(f"Skipping {repo_full_name} due to clone failure.")
            continue
            
        repo_findings = []
        if args.mode == 'history':
            logger.info(f"Scanning history (depth={args.depth}, max_file_age={args.file_age}m)...")
            repo_findings = repo_processor.scan_history(local_path, depth=args.depth, scanner_func=matcher.scan_text, max_file_age_months=args.file_age)
        else:
            logger.info(f"Scanning current files (max_file_age={args.file_age}m)...")
            repo_findings = repo_processor.scan_current_files(local_path, scanner_func=matcher.scan_text, max_file_age_months=args.file_age)
            
        # Post-process findings to add repo metadata
        for f in repo_findings:
            f['repo'] = html_url
            # Construct file URL if possible
            # https://github.com/user/repo/blob/commit/path
            if 'file_diff: ' in f.get('location', ''):
                path = f['location'].replace('file_diff: ', '')
                f['file_url'] = f"{html_url}/blob/{f['commit']}/{path}"
            elif 'file: ' in f.get('location', ''):
                # local path to relative
                rel_path = f['location'].replace('file: ', '').replace(local_path, '').replace('\\', '/').lstrip('/')
                f['file_url'] = f"{html_url}/blob/HEAD/{rel_path}"
            else:
                f['file_url'] = "N/A"
                
        if repo_findings:
            logger.warning(f"FOUND {len(repo_findings)} SECRETS in {repo_full_name}!")
            if OUTPUT_FORMAT == 'json':
                save_results_json(repo_findings, results_file)
            else:
                save_results(repo_findings, results_file)
            total_findings += len(repo_findings)
        else:
            logger.info(f"No secrets found in {repo_full_name}.")
        
        # Mark as scanned (if it has a valid ID)
        if repo_id and repo_id != "manual":
            mark_as_scanned(repo_id)
            
        # Cleanup
        repo_processor.delete_repo(local_path)
    
    logger.info(f"Scan complete. Total findings: {total_findings}. Results saved to {results_file}")

if __name__ == "__main__":
    main()
