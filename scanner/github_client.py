import requests
import random

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    def search_repositories(self, max_stars=10, limit=5, exclude_ids=None, min_created_date=None):
        """
        Finds random repositories using the GitHub Search API.
        We use random character queries + star filters to find diverse, non-popular repos.
        """
        if exclude_ids is None:
            exclude_ids = set()
            
        found_repos = []
        attempts = 0
        max_attempts = 20
        
        # Random queries to sample different parts of GitHub
        # Using 1-2 random characters cover a huge surface area
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        
        while len(found_repos) < limit and attempts < max_attempts:
            attempts += 1
            
            # Generate a random query: e.g. "a", "xk", "test"
            query_len = random.choice([1, 2])
            query_str = "".join(random.choice(chars) for _ in range(query_len))
            
            # Random sort order to further shuffle
            sort_order = random.choice(["updated", "stars", "forks"])
            
            # Random page (1-10) to avoid always getting the top results for 'a'
            page = random.randint(1, 10)
            
            search_url = f"{self.base_url}/search/repositories"
            
            # precise filter: query + max stars + recent push (optional, to avoid dead repos)
            q = f"{query_str} stars:<={max_stars} pushed:>2024-01-01 size:>0"
            
            if min_created_date:
                q += f" created:>{min_created_date}"
            
            params = {
                "q": q,
                "sort": sort_order,
                "order": "desc", # or asc
                "per_page": 100, # fetch more to filter locally if needed
                "page": page
            }
            
            try:
                print(f"Searching: {q} (Page {page})...")
                response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    if not items:
                        continue
                        
                    # Shuffle the page results
                    random.shuffle(items)
                    
                    for item in items:
                        if len(found_repos) >= limit:
                            break
                            
                        # ID Check
                        repo_id = str(item.get('id'))
                        if repo_id in exclude_ids:
                            continue
                        
                        # Double check stars (API is usually good, but safe to verify)
                        if item.get('stargazers_count', 0) > max_stars:
                            continue
                            
                        # Add to list
                        found_repos.append(item)
                        exclude_ids.add(repo_id) # Temporary add to prevent dupes in same batch
                        
                elif response.status_code == 403 or response.status_code == 429:
                    print("GitHub API Rate Limit Exceeded. Waiting...")
                    break
                else:
                    print(f"Search API Error: {response.status_code}")
                    
            except Exception as e:
                print(f"Network error during search: {e}")
                
        return found_repos

    # Removed _search_with_filtering as it is now integrated into the main method.


if __name__ == "__main__":
    import sys
    import os
    import json
    
    # Add parent directory to path to import config
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    
    client = GitHubClient(token=config.GITHUB_TOKEN)
    repos = client.search_repositories(max_stars=10, limit=5)
    
    # Ensure cache directory exists
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    output_file = os.path.join(cache_dir, "found_repos.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=4, ensure_ascii=False)
        
    print(f"Found {len(repos)} repositories. Results saved to: {output_file}")