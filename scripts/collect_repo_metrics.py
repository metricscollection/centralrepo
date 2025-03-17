name: Repository Metrics Tracker

on:
  # Run on any commit to main branch
  push:
    branches:
      - main
  # Run on schedule
  schedule:
    # Run daily at midnight
    - cron: '0 0 * * *'
  # Allow manual trigger
  workflow_dispatch:

# Add permissions for the GitHub token
permissions:
  contents: write

jobs:
  track-metrics:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          clean: true  # Ensure a clean working copy
          fetch-depth: 1  # Shallow clone for faster checkout
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install PyGithub tabulate PyYAML
      
      - name: Run metrics collection
        run: |
          echo "Starting metrics collection..."
          echo "GitHub Repository: $GITHUB_REPOSITORY"
          echo "Running with organization specified in config..."
          # Run with debug flag
          python scripts/collect_repo_metrics.py --config config/repos.yaml --debug
          
          # Print the contents of the metrics report file
          echo "========== GENERATED METRICS REPORT =========="
          cat metrics_report.md
          echo "=============================================="
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_API_TOKEN }}
          GITHUB_ORG: metricscollection
      
      - name: Save metrics to artifact
        uses: actions/upload-artifact@v4
        with:
          name: repository-metrics
          path: metrics_report.md
      
      # Commit and push the metrics report
      - name: Commit metrics report
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Update repository metrics report [CI]"
          file_pattern: "metrics_report.md"
          commit_user_name: "GitHub Actions"
          commit_user_email: "github-actions@github.com"
          push_options: "--force"
