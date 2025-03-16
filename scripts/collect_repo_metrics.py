#!/usr/bin/env python3
"""
Repository Metrics Collector

This script reads a list of repositories from a configuration file
and collects metrics like last commit date for each repository.
"""

import os
import yaml
import datetime
from github import Github
from tabulate import tabulate
import time

def load_repo_list(config_file="config/repos.yaml"):
    """Load repository list from YAML configuration file."""
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config.get('repos', [])

def get_org_name_from_env():
    """Get organization name from environment variable."""
    repo_path = os.environ.get('GITHUB_REPOSITORY', '')
    if '/' in repo_path:
        org_name = repo_path.split('/')[0]
        print(f"Detected organization name from GITHUB_REPOSITORY: {org_name}")
        return org_name
    
    # If we can't get it from environment, try reading it from a config file
    try:
        with open("config/organization.yaml", 'r') as file:
            config = yaml.safe_load(file)
            org_name = config.get('organization', '')
            if org_name:
                print(f"Read organization name from config file: {org_name}")
                return org_name
    except FileNotFoundError:
        pass
    
    # Fallback - you might want to replace this with your actual org name
    print("Warning: Could not determine organization name from environment or config.")
    print("Using command-line argument or falling back to default.")
    return os.environ.get('GITHUB_ORG', 'defaultOrgName')

def collect_metrics(g, org_name, repo_names):
    """Collect metrics for the specified repositories."""
    metrics = []
    
    print(f"Organization name: {org_name}")
    
    try:
        org = g.get_organization(org_name)
    except Exception as e:
        print(f"Error accessing organization {org_name}: {str(e)}")
        return [{'Repository': repo_name, 
                'Last Commit': f'Org error: {str(e)}',
                'Open Issues': 'Error', 
                'Last Release': 'Error', 
                'Contributors': 'Error'} for repo_name in repo_names]
    
    for repo_name in repo_names:
        print(f"Processing repository: {repo_name}")
        
        try:
            # Get repository with fresh data
            repo = org.get_repo(repo_name)
            
            # Get last commit date and author
            try:
                # Try with per_page parameter (newer PyGithub versions)
                commits = list(repo.get_commits(per_page=1))
            except TypeError:
                # Fall back to older PyGithub versions without per_page
                commits = list(repo.get_commits())[:1]
                
            if commits:
                last_commit_date = commits[0].commit.author.date
                # Get the author name from the commit
                last_commit_author = commits[0].commit.author.name
                # Format the date
                if isinstance(last_commit_date, datetime.datetime):
                    last_commit_date = last_commit_date.strftime('%Y-%m-%d %H:%M:%S')
                last_commit_info = f"{last_commit_date} by {last_commit_author}"
            else:
                last_commit_info = "No commits"
            
            # Get number of open issues
            open_issues_count = repo.open_issues_count
            
            # Get last release date if available
            try:
                # Try with per_page parameter (newer PyGithub versions)
                releases = list(repo.get_releases(per_page=1))
            except TypeError:
                # Fall back to older PyGithub versions without per_page
                releases = list(repo.get_releases())[:1]
                
            last_release = releases[0].published_at.strftime('%Y-%m-%d %H:%M:%S') if releases else "No releases"
            
            # Get contributors count
            contributors = list(repo.get_contributors())
            contributors_count = len(contributors)
            
            metrics.append({
                'Repository': repo_name,
                'Last Commit': last_commit_info,
                'Open Issues': open_issues_count,
                'Last Release': last_release,
                'Contributors': contributors_count
            })
            
            # Avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing repository {repo_name}: {str(e)}")
            metrics.append({
                'Repository': repo_name,
                'Last Commit': f'Error: {str(e)}',
                'Open Issues': 'Error',
                'Last Release': 'Error',
                'Contributors': 'Error'
            })
    
    return metrics

def generate_report(metrics, output_file="metrics_report.md"):
    """Generate a markdown report from the collected metrics."""
    import os
    
    headers = ['Repository', 'Last Commit', 'Open Issues', 'Last Release', 'Contributors']
    table = tabulate(
        [[m[h] for h in headers] for m in metrics],
        headers=headers,
        tablefmt="github"
    )
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create directory for output file if it doesn't exist
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(f"# Repository Metrics Report\n\n")
        f.write(f"Generated on: {timestamp}\n\n")
        f.write(table)
        f.write("\n\n")
        f.write("## Summary\n\n")
        f.write(f"Total repositories: {len(metrics)}\n")
        
        # Calculate how many repos were updated in the last week
        one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        active_repos = sum(1 for m in metrics if isinstance(m['Last Commit'], str) 
                           and not m['Last Commit'].startswith('Error')
                           and m['Last Commit'].split(' by ')[0] >= one_week_ago)
        f.write(f"Repositories with commits in the last week: {active_repos}\n")
    
    print(f"Report generated: {output_file}")

def main():
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Collect repository metrics')
    parser.add_argument('--org', help='GitHub organization name')
    parser.add_argument('--config', default='config/repos.yaml', help='Path to repository configuration file')
    args = parser.parse_args()
    
    # Get GitHub token from environment
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token not found. Set the GITHUB_TOKEN environment variable.")
        return
    
    # Initialize GitHub API client with per_page=1 to minimize API calls
    g = Github(token, per_page=1)
    
    # Get organization name
    org_name = args.org or get_org_name_from_env()
    if not org_name:
        print("Error: Could not determine organization name.")
        return
    
    print(f"Collecting metrics for organization: {org_name}")
    
    # Load repository list
    repo_names = load_repo_list(args.config)
    if not repo_names:
        print("Error: No repositories found in configuration file.")
        return
    
    print(f"Found {len(repo_names)} repositories to process.")
    
    # Collect metrics
    metrics = collect_metrics(g, org_name, repo_names)
    
    # Generate report
    generate_report(metrics)
    
    print("Metrics collection completed successfully.")

if __name__ == "__main__":
    main()
