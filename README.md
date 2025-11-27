# Go Green

Generate backdated git commits to enhance your GitHub activity graph.

## Overview

Go Green is a Python-based CLI tool that creates trivial git commits with backdated timestamps. It features intelligent randomization with configurable weights for weekends vs weekdays, automatic vacation weeks, and reduces activity around US holidays for a realistic commit pattern. By default, it creates light weekday activity (only 1-2 weekdays per week) and heavier weekend activity, with 2 vacation weeks per year.

## Features

- **Tunable Randomization**: Configure min/max commits per day
- **Weighted Activity**: Adjust activity levels for weekends vs weekdays independently
- **Realistic Weekday Patterns**: Low weekday activity (1-2 days per week) for natural-looking commit history
- **Vacation Weeks**: Automatic vacation weeks (1-2 per year) with zero commits for the entire week
- **Holiday Awareness**: Automatically reduces commits around US holidays (Christmas, New Year, etc.)
- **Work Hours Simulation**: Commits are timestamped during working hours (9 AM - 6 PM)
- **Dry Run Mode**: Preview commits before creating them
- **Docker Support**: Fully containerized development and execution environment
- **Real-time Progress**: Visual progress bar shows commit creation status
- **Clear Command**: Easy removal of generated commits

## Requirements

- Docker and Docker Compose
- Git repository (the tool operates on the current repository)

## Installation & Setup

### Using Docker (Recommended)

1. Clone or navigate to this repository:
```bash
cd go-green
```

2. Build the Docker image:
```bash
docker-compose build
```

This will install all dependencies and set up the Python environment inside the container.

## Usage

### Quick Start

1. **Initialize a git repository** (if not already done):
```bash
git init
```

2. **Preview what commits would be created** (dry run):
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --dry-run
```

3. **Create the commits**:
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31"
```

4. **Push to GitHub** (if you have a remote configured):
```bash
git push origin main
```

### Basic Commands

**Generate commits:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31"
```

**Clear generated commits:**
```bash
docker-compose run --rm go-green clear
```

**View help:**
```bash
docker-compose run --rm go-green --help
docker-compose run --rm go-green main --help
docker-compose run --rm go-green clear --help
```

### Commands

Go Green has two main commands:

#### `main` - Generate commits

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--start-date` | `-s` | Start date (ISO format or natural language) | Required |
| `--end-date` | `-e` | End date (ISO format or natural language) | Required |
| `--min-commits` | `-n` | Minimum commits per day | 1 |
| `--max-commits` | `-x` | Maximum commits per day | 3 |
| `--weekend-weight` | `-w` | Weekend activity multiplier | 1.5 |
| `--weekday-weight` | | Weekday activity multiplier | 0.2 |
| `--holiday-weight` | `-h` | Holiday activity multiplier | 0.3 |
| `--vacation-weeks` | `-v` | Vacation weeks per year (no commits) | 2 |
| `--dry-run` | `-d` | Preview without creating commits | False |
| `--repo-path` | `-r` | Path to git repository | Current directory |

#### `clear` - Remove generated commits

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--dry-run` | `-d` | Preview what would be removed | False |
| `--repo-path` | `-r` | Path to git repository | Current directory |

### Examples

#### Generating Commits

**Preview commits for the past year with default settings:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --dry-run
```

**Create commits with more weekend activity:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --weekend-weight 2.0
```

**Realistic pattern with light weekdays and heavy weekends (recommended):**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --weekday-weight 0.2 \
  --weekend-weight 2.0 \
  --vacation-weeks 2
```

**Minimal holiday activity:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --holiday-weight 0.1
```

**High activity across all days:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --min-commits 5 \
  --max-commits 10 \
  --weekend-weight 1.0
```

**Using natural language dates:**
```bash
docker-compose run --rm go-green main \
  --start-date "January 1, 2024" \
  --end-date "December 31, 2024"
```

**More vacation weeks for long-term contributors:**
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --vacation-weeks 4 \
  --weekday-weight 0.15
```

#### Clearing Commits

**Preview what would be removed:**
```bash
docker-compose run --rm go-green clear --dry-run
```

**Remove all activity.log commits:**
```bash
docker-compose run --rm go-green clear
```

## How It Works

### Generating Commits

1. **Vacation Week Selection**: Randomly selects vacation weeks (entire weeks with no commits) based on `vacation-weeks` parameter
2. **Date Range Iteration**: The tool iterates through each day in the specified date range
3. **Weighted Calculation**: For each day, it calculates how many commits to create based on:
   - Whether it's in a vacation week (no commits)
   - Whether it's a US holiday (applies `holiday-weight`)
   - Whether it's a weekend (applies `weekend-weight`)
   - Whether it's a weekday (applies `weekday-weight`)
   - Random selection within `min-commits` and `max-commits` range
4. **Time Randomization**: Each commit gets a random timestamp during work hours (9 AM - 6 PM)
5. **Commit Creation**: Appends an entry to `activity.log` and creates a git commit with the backdated timestamp
6. **Progress Tracking**: Displays a real-time progress bar showing commits created, percentage complete, and elapsed time

### Clearing Commits

1. **Commit Scanning**: Iterates through all commits in the repository
2. **Identification**: Identifies commits where the only file changed was `activity.log`
3. **Removal**: Resets the repository to the last commit before the activity commits
4. **Cleanup**: Removes the `activity.log` file if all commits were activity commits

## Weight System Explained

- **Weekday Weight** (New!):
  - `0.2` = Only ~20% of weekdays will have commits (default, recommended for realism)
  - `0.5` = ~50% of weekdays will have commits
  - `1.0` = All weekdays have commits (less realistic)
  - Lower values create more realistic patterns with sporadic weekday activity

- **Weekend Weight**:
  - `1.0` = Same activity as weekdays (with weekday weight applied)
  - `> 1.0` = More activity on weekends (e.g., `1.5` = 50% more)
  - `< 1.0` = Less activity on weekends (e.g., `0.5` = 50% less)

- **Holiday Weight**:
  - `0.3` = 70% chance of no commits on holidays
  - `0.0` = No commits on holidays
  - `1.0` = Normal activity on holidays

- **Vacation Weeks** (New!):
  - `2` = Two random weeks per year with zero commits (default)
  - `0` = No vacation weeks
  - `4` = Four vacation weeks per year (recommended for longer time ranges)
  - Vacation weeks are randomly distributed and avoid major holiday periods

## Typical Workflow

### First Time Setup

1. **Navigate to the project**:
```bash
cd go-green
```

2. **Build the Docker image**:
```bash
docker-compose build
```

3. **Initialize git if needed**:
```bash
git init
```

4. **Test with dry run**:
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --dry-run
```

### Generating Activity

1. **Create commits**:
```bash
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31"
```

2. **Review the commits**:
```bash
git log --oneline
```

3. **If using GitHub, push to remote**:
```bash
# First time setup
git remote add origin https://github.com/yourusername/go-green.git
git branch -M main

# Push commits
git push -u origin main
```

### Modifying or Clearing

1. **If you want to adjust and regenerate**:
```bash
# Clear existing commits
docker-compose run --rm go-green clear

# Create new ones with different parameters
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --min-commits 2 \
  --max-commits 5
```

2. **If you already pushed to remote**:
```bash
# After clearing locally
docker-compose run --rm go-green clear

# Force push to update remote
git push --force origin main

# WARNING: Only do this if you're sure!
```

## Project Structure

```
go-green/
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Python project configuration
├── README.md              # This file
├── .gitignore
├── .dockerignore
└── src/
    └── go_green/
        ├── __init__.py
        ├── __main__.py          # Entry point
        ├── cli.py               # CLI interface (Typer)
        └── commit_generator.py  # Core commit generation logic
```

## Development

### Local Development (without Docker)

If you prefer to develop without Docker:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in editable mode
pip install -e .

# Run the tool
python -m go_green --help
python -m go_green main --start-date "2024-01-01" --end-date "2024-12-31"
```

### Running Tests

The tool includes built-in dry-run mode for testing:

```bash
# Test commit generation without creating commits
docker-compose run --rm go-green main \
  --start-date "2024-01-01" \
  --end-date "2024-12-31" \
  --dry-run

# Test commit clearing without removing commits
docker-compose run --rm go-green clear --dry-run
```

## Important Notes

- This tool modifies git history by creating backdated commits
- The commits are real git commits with manipulated timestamps
- Use `--dry-run` first to preview what will be created
- The tool appends to `activity.log` - this file should not be in `.gitignore`
- Commits are sorted chronologically before creation
- US holiday calendar is used for holiday detection
- **Progress bar**: During commit creation, you'll see a real-time progress bar showing:
  - Number of commits created
  - Percentage complete
  - Time elapsed
- **Force push warning**: If you've already pushed commits and then clear them locally, you'll need to force push to update the remote (use with caution!)

## Troubleshooting

### "Not a git repository" error
Make sure you're in a git repository or run `git init` first.

### Permission denied errors
On Linux/Mac, you may need to adjust Docker volume permissions or run with appropriate user flags.

### Commits not showing on GitHub
1. Make sure you've pushed to the remote: `git push origin main`
2. Check that your email in git config matches your GitHub email
3. GitHub may take a few minutes to update the activity graph

### Want to start over
```bash
# Clear all generated commits
docker-compose run --rm go-green clear

# Verify they're gone
git log --oneline
```

## License

MIT

## Disclaimer

This tool is for educational and personal use. Be mindful of how you represent your activity on platforms like GitHub. Manipulating commit history to misrepresent your actual development activity may violate platform terms of service or professional ethics guidelines.
