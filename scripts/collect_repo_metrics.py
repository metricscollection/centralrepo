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
    return os.environ.get('GITHUB_REPOSITORY', '').split('/')[0]

def collect_metrics(g, org_name, repo_names):
    """Collect metrics for the specified repositories."""
    metrics = []
    org = g.get_organization(org_name)
    
    for repo_name in repo_names:
        print(f"Processing repository: {repo_name}")
        
        try:
            repo = org.get_repo(repo_name)
            
            # Get last commit date
            commits = list(repo.get_commits(per_page=1))
            last_commit_date = commits[0].commit.author.date if commits else "No commits"
            
            # Format the date
            if isinstance(last_commit_date, datetime.datetime):
                last_commit_date = last_commit_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get number of open issues
            open_issues_count = repo.open_issues_count
            
            # Get last release date if available
            releases = list(repo.get_releases(per_page=1))
            last_release = releases[0].published_at.strftime('%Y-%m-%d %H:%M:%S') if releases else "No releases"
            
            # Get contributors count
            contributors = list(repo.get_contributors())
            contributors_count = len(contributors)
            
            metrics.append({
                'Repository': repo_name,
                'Last Commit': last_commit_date,
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
                'Last Commit': 'Error',
                'Open Issues': 'Error',
                'Last Release': 'Error',
                'Contributors': 'Error'
            })
    
    return metrics

def generate_report(metrics, output_file="metrics_report.md"):
    """Generate a markdown report from the collected metrics."""
    headers = ['Repository', 'Last Commit', 'Open Issues', 'Last Release', 'Contributors']
    table = tabulate(
        [[m[h] for h in headers] for m in metrics],
        headers=headers,
        tablefmt="github"
    )
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(output_file, 'w') as f:
        f.write(f"# Repository Metrics Report\n\n")
        f.write(f"Generated on: {timestamp}\n\n")
        f.write(table)
        f.write("\n\n")
        f.write("## Summary\n\n")
        f.write(f"Total repositories: {len(metrics)}\n")
        
        # Calculate how many repos were updated in the last week
        one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        active_repos = sum(1 for m in metrics if isinstance(m['Last Commit'], str) and m['Last Commit'] >= one_week_ago)
        f.write(f"Repositories with commits in the last week: {active_repos}\n")

def main():
    # Get GitHub token from environment
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token not found. Set the GITHUB_TOKEN environment variable.")
        return
    
    # Initialize GitHub API client
    g = Github(token)
    
    # Get organization name
    org_name = get_org_name_from_env()
    if not org_name:
        print("Error: Could not determine organization name.")
        return
    
    print(f"Collecting metrics for organization: {org_name}")
    
    # Load repository list
    repo_names = load_repo_list()
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
