#!/usr/bin/env python3
"""
Repository Metrics Collector

This script reads a list of repositories from a configuration file
and collects metrics like last commit date for each repository.
"""

import os
import yaml
import datetime
import time
import argparse
from github import Github
import github
from tabulate import tabulate

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
                'Owner': 'Error',
                'Last Commit': f'Org error: {str(e)}',
                'Open Issues': 'Error', 
                'Last Release': 'Error',
                'Commits (Week)': 0,
                'Commits (Month)': 0,
                'Contributors': 'Error'} for repo_name in repo_names]
    
    # Get current date for time-based calculations
    current_time = datetime.datetime.now()
    one_week_ago = current_time - datetime.timedelta(days=7)
    one_month_ago = current_time - datetime.timedelta(days=30)
    
    for repo_name in repo_names:
        print(f"Processing repository: {repo_name}")
        
        try:
            # Get repository with fresh data
            repo = org.get_repo(repo_name)
            
            # Get repository owner
            repo_owner = repo.owner.login
            
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
            
            # Count commits for past week and month - simplified approach
            try:
                print(f"Counting commits for {repo_name}...")
                
                # Simple approach - just get all commits and count manually
                all_commits = list(repo.get_commits())
                print(f"Retrieved {len(all_commits)} total commits for {repo_name}")
                
                # Count commits in time windows
                now = datetime.datetime.now()
                week_ago = now - datetime.timedelta(days=7)
                month_ago = now - datetime.timedelta(days=30)
                
                weekly_commits = 0
                monthly_commits = 0
                
                for commit in all_commits:
                    commit_date = commit.commit.author.date
                    if commit_date >= month_ago:
                        monthly_commits += 1
                        if commit_date >= week_ago:
                            weekly_commits += 1
                
                print(f"Found {weekly_commits} weekly commits and {monthly_commits} monthly commits for {repo_name}")
                
            except Exception as e:
                print(f"Error counting commits for {repo_name}: {str(e)}")
                weekly_commits = 0
                monthly_commits = 0
            
            metrics.append({
                'Repository': repo_name,
                'Owner': repo_owner,
                'Last Commit': last_commit_info,
                'Open Issues': open_issues_count,
                'Last Release': last_release,
                'Commits (Week)': weekly_commits,
                'Commits (Month)': monthly_commits,
                'Contributors': contributors_count
            })
            
            # Avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing repository {repo_name}: {str(e)}")
            metrics.append({
                'Repository': repo_name,
                'Owner': 'Error',
                'Last Commit': f'Error: {str(e)}',
                'Open Issues': 'Error',
                'Last Release': 'Error',
                'Commits (Week)': 0,
                'Commits (Month)': 0,
                'Contributors': 'Error'
            })
    
    return metrics

def generate_report(metrics, output_file="metrics_report.md"):
    """Generate a markdown report from the collected metrics."""
    import os
    
    # Make sure all metrics have valid values
    for m in metrics:
        # Set numeric types to 0 if they have errors
        for key in ['Commits (Week)', 'Commits (Month)']:
            if not isinstance(m.get(key), int):
                m[key] = 0
    
    headers = ['Repository', 'Owner', 'Last Commit', 'Open Issues', 'Last Release', 'Commits (Week)', 'Commits (Month)', 'Contributors']
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
        
        # Add total commit metrics
        total_weekly_commits = sum(m['Commits (Week)'] for m in metrics 
                                  if isinstance(m['Commits (Week)'], int))
        total_monthly_commits = sum(m['Commits (Month)'] for m in metrics 
                                   if isinstance(m['Commits (Month)'], int))
        f.write(f"Total commits in the last week: {total_weekly_commits}\n")
        f.write(f"Total commits in the last month: {total_monthly_commits}\n")
    
    print(f"Report generated: {output_file}")

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Collect repository metrics')
    parser.add_argument('--org', help='GitHub organization name')
    parser.add_argument('--config', default='config/repos.yaml', help='Path to repository configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Enable debug mode
    debug_mode = args.debug
    
    # Get GitHub token from environment
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token not found. Set the GITHUB_TOKEN environment variable.")
        return
    
    # Initialize GitHub API client with per_page=100 to get more commits
    g = Github(token, per_page=100)
    
    # Print GitHub version info
    if debug_mode:
        print(f"PyGithub version info: {github.__version__}")
    
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
