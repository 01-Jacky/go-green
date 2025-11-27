"""CLI interface for Go Green."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table

from .commit_generator import CommitGenerator

app = typer.Typer(
    help="Generate backdated git commits to enhance GitHub activity",
    add_completion=False,
)
console = Console()


@app.command()
def main(
    start_date: str = typer.Option(
        ...,
        "--start-date",
        "-s",
        help="Start date (e.g., '2024-01-01' or 'January 1, 2024')",
    ),
    end_date: str = typer.Option(
        ...,
        "--end-date",
        "-e",
        help="End date (e.g., '2024-12-31' or 'December 31, 2024')",
    ),
    min_commits: int = typer.Option(
        1,
        "--min-commits",
        "-n",
        help="Minimum commits per day",
        min=0,
    ),
    max_commits: int = typer.Option(
        3,
        "--max-commits",
        "-x",
        help="Maximum commits per day",
        min=1,
    ),
    weekend_weight: float = typer.Option(
        1.5,
        "--weekend-weight",
        "-w",
        help="Multiplier for weekend activity (e.g., 1.5 = 50%% more, 0.5 = 50%% less)",
        min=0.0,
    ),
    weekday_weight: float = typer.Option(
        0.2,
        "--weekday-weight",
        help="Multiplier for weekday activity (e.g., 0.2 = only 20%% of days have commits)",
        min=0.0,
        max=1.0,
    ),
    holiday_weight: float = typer.Option(
        0.3,
        "--holiday-weight",
        "-h",
        help="Multiplier for holiday activity (e.g., 0.3 = 70%% less)",
        min=0.0,
    ),
    vacation_weeks_per_year: int = typer.Option(
        2,
        "--vacation-weeks",
        "-v",
        help="Number of vacation weeks per year (entire week with no commits)",
        min=0,
        max=10,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview commits without creating them",
    ),
    repo_path: Optional[Path] = typer.Option(
        None,
        "--repo-path",
        "-r",
        help="Path to git repository (defaults to current directory)",
    ),
) -> None:
    """
    Generate backdated git commits with configurable randomness and weighting.

    This tool creates trivial commits (appending to activity.log) with backdated
    timestamps to fill in GitHub activity. It supports weighted randomness for
    weekends vs weekdays and automatically reduces activity around US holidays.
    """
    # Validate parameters
    if min_commits > max_commits:
        console.print(
            "[red]Error:[/red] min-commits cannot be greater than max-commits",
            style="bold",
        )
        raise typer.Exit(1)

    # Default to current directory
    if repo_path is None:
        repo_path = Path.cwd()

    # Verify it's a git repository
    if not (repo_path / ".git").exists():
        console.print(
            f"[red]Error:[/red] {repo_path} is not a git repository",
            style="bold",
        )
        raise typer.Exit(1)

    console.print("\n[bold cyan]Go Green - Git Activity Generator[/bold cyan]\n")

    # Display configuration
    config_table = Table(title="Configuration", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="yellow")

    config_table.add_row("Repository", str(repo_path))
    config_table.add_row("Date Range", f"{start_date} to {end_date}")
    config_table.add_row("Commits per Day", f"{min_commits} - {max_commits}")
    config_table.add_row("Weekend Weight", f"{weekend_weight}x")
    config_table.add_row("Weekday Weight", f"{weekday_weight}x")
    config_table.add_row("Holiday Weight", f"{holiday_weight}x")
    config_table.add_row("Vacation Weeks/Year", str(vacation_weeks_per_year))
    config_table.add_row("Mode", "DRY RUN" if dry_run else "LIVE")

    console.print(config_table)
    console.print()

    try:
        # Initialize generator
        generator = CommitGenerator(
            repo_path=repo_path,
            min_commits=min_commits,
            max_commits=max_commits,
            weekend_weight=weekend_weight,
            weekday_weight=weekday_weight,
            holiday_weight=holiday_weight,
            vacation_weeks_per_year=vacation_weeks_per_year,
        )

        # Generate commits with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                "[green]Creating commits..." if not dry_run else "[yellow]Simulating commits...",
                total=None,  # Will be updated once we know the total
            )

            # Progress callback to update the progress bar
            def update_progress(current: int, total: int, commit_datetime) -> None:
                if current == 1:
                    # Update total on first call
                    progress.update(task_id, total=total)
                progress.update(
                    task_id,
                    completed=current,
                    description=f"[green]Creating commits..." if not dry_run else f"[yellow]Simulating commits..."
                )

            commits = generator.generate_commits(
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run,
                progress_callback=update_progress,
            )

        # Display results
        console.print(
            f"\n[bold green]✓[/bold green] Successfully {'simulated' if dry_run else 'created'} "
            f"{len(commits)} commit(s)\n"
        )

        if commits:
            # Show sample of commits
            sample_size = min(10, len(commits))
            console.print(f"[dim]Showing first {sample_size} commits:[/dim]\n")

            for i, commit_time in enumerate(commits[:sample_size], 1):
                day_name = commit_time.strftime("%A")
                console.print(
                    f"  {i:2d}. {commit_time.strftime('%Y-%m-%d %H:%M:%S')} ({day_name})"
                )

            if len(commits) > sample_size:
                console.print(f"\n  [dim]... and {len(commits) - sample_size} more[/dim]")

        if dry_run:
            console.print(
                "\n[yellow]This was a dry run. No commits were created.[/yellow]"
            )
            console.print(
                "[dim]Remove --dry-run flag to create actual commits.[/dim]\n"
            )
        else:
            console.print(
                "\n[green]Commits have been created with backdated timestamps.[/green]"
            )
            console.print(
                "[dim]Use 'git log' to view the commit history.[/dim]\n"
            )

    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}\n", style="bold")
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"\n[red]Unexpected error:[/red] {e}\n",
            style="bold",
        )
        raise typer.Exit(1)


@app.command()
def clear(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview what would be removed without actually removing commits",
    ),
    repo_path: Optional[Path] = typer.Option(
        None,
        "--repo-path",
        "-r",
        help="Path to git repository (defaults to current directory)",
    ),
) -> None:
    """
    Remove all commits that only modified activity.log.

    This command identifies and removes all commits created by Go Green
    (commits where the only file changed was activity.log).
    """
    # Default to current directory
    if repo_path is None:
        repo_path = Path.cwd()

    # Verify it's a git repository
    if not (repo_path / ".git").exists():
        console.print(
            f"[red]Error:[/red] {repo_path} is not a git repository",
            style="bold",
        )
        raise typer.Exit(1)

    console.print("\n[bold cyan]Go Green - Clear Activity Commits[/bold cyan]\n")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No commits will be removed[/yellow]\n")

    try:
        # Initialize generator
        generator = CommitGenerator(repo_path=repo_path)

        # Clear commits
        with console.status(
            "[bold yellow]Scanning commits..." if dry_run else "[bold red]Removing commits...",
            spinner="dots",
        ):
            removed_count = generator.clear_commits(dry_run=dry_run)

        # Display results
        if removed_count == 0:
            console.print(
                "\n[yellow]No activity.log commits found to remove.[/yellow]\n"
            )
        else:
            action = "would be removed" if dry_run else "removed"
            console.print(
                f"\n[bold green]✓[/bold green] {removed_count} commit(s) {action}\n"
            )

            if dry_run:
                console.print(
                    "[yellow]This was a dry run. No commits were removed.[/yellow]"
                )
                console.print(
                    "[dim]Remove --dry-run flag to actually remove commits.[/dim]\n"
                )
            else:
                console.print(
                    "[green]Activity commits have been removed.[/green]"
                )
                console.print(
                    "[dim]Use 'git log' to verify the commit history.[/dim]\n"
                )
                console.print(
                    "[red]WARNING:[/red] If you've already pushed these commits, "
                    "you'll need to force push to update the remote.\n"
                )

    except Exception as e:
        console.print(
            f"\n[red]Unexpected error:[/red] {e}\n",
            style="bold",
        )
        raise typer.Exit(1)
