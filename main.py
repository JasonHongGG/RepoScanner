import logging
import argparse
from utils.logger import setup_logger
from scanner.scanner_engine import ScannerEngine

def main():
    logger = setup_logger()
    
    parser = argparse.ArgumentParser(description="GitHub Secret Scanner")
    parser.add_argument("--mode", choices=["current", "history"], default="current", help="Scan mode")
    parser.add_argument("--depth", type=int, default=10, help="Commit depth for history scan")
    parser.add_argument("--count", type=int, default=5, help="Number of repositories to scan")
    parser.add_argument("--max-stars", type=int, default=10, help="Max stars for target repos")
    parser.add_argument("--repo-age", type=int, default=0, help="Repo age in months (0=any)")
    parser.add_argument("--file-age", type=int, default=0, help="File age in months (0=any)")
    parser.add_argument("--repo", type=str, help="Specific repository URL to scan (bypasses random search)")
    
    args = parser.parse_args()
    
    engine = ScannerEngine()
    engine.run(args)

if __name__ == "__main__":
    main()
