"""Core logic for generating backdated git commits."""

import random
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Callable, List, Optional

import holidays
from dateutil import parser
from git import Repo


class CommitGenerator:
    """Generates backdated git commits with weighted randomness."""

    def __init__(
        self,
        repo_path: Path,
        min_commits: int = 1,
        max_commits: int = 3,
        weekend_weight: float = 1.5,
        weekday_weight: float = 0.2,
        holiday_weight: float = 0.3,
        vacation_weeks_per_year: int = 2,
    ) -> None:
        """
        Initialize the commit generator.

        Args:
            repo_path: Path to the git repository
            min_commits: Minimum commits per day
            max_commits: Maximum commits per day
            weekend_weight: Multiplier for weekend activity (>1.0 for more, <1.0 for less)
            weekday_weight: Multiplier for weekday activity (typically <1.0 for less)
            holiday_weight: Multiplier for holiday activity (typically <1.0 for less)
            vacation_weeks_per_year: Number of vacation weeks per year (0 commits)
        """
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.min_commits = min_commits
        self.max_commits = max_commits
        self.weekend_weight = weekend_weight
        self.weekday_weight = weekday_weight
        self.holiday_weight = holiday_weight
        self.vacation_weeks_per_year = vacation_weeks_per_year
        self.us_holidays = holidays.US()
        self.activity_log_path = repo_path / "activity.log"
        self.vacation_weeks = []  # Will be populated in generate_commits
        self.current_week_start = None  # Track current week for weekday selection
        self.selected_weekdays = set()  # Weekdays selected for commits in current week

    def _is_weekend(self, date: datetime) -> bool:
        """Check if date falls on a weekend (Saturday=5, Sunday=6)."""
        return date.weekday() >= 5

    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a US holiday."""
        return date.date() in self.us_holidays

    def _get_week_start(self, date: datetime) -> datetime:
        """Get the Monday of the week for a given date."""
        return date - timedelta(days=date.weekday())

    def _is_vacation_week(self, date: datetime) -> bool:
        """Check if date falls within a vacation week."""
        week_start = self._get_week_start(date)
        return week_start in self.vacation_weeks

    def _select_weekdays_for_week(self, week_start: datetime) -> set:
        """
        Select which weekdays (Mon-Fri) should have commits for a given week.
        Selects 1-3 weekdays to maintain realistic work patterns.

        Args:
            week_start: Monday of the week

        Returns:
            Set of weekday numbers (0=Monday, 4=Friday) that should have commits
        """
        # Select 1-3 weekdays randomly for a realistic work pattern
        # Lower weights favor fewer weekdays
        if self.weekday_weight < 0.3:
            # Low weight: 1-2 weekdays
            num_weekdays = random.randint(1, 2)
        elif self.weekday_weight < 0.6:
            # Medium weight: 2-3 weekdays
            num_weekdays = random.randint(2, 3)
        else:
            # Higher weight: 3-4 weekdays
            num_weekdays = random.randint(3, 4)

        # Randomly select weekdays (0=Monday through 4=Friday)
        all_weekdays = list(range(5))
        return set(random.sample(all_weekdays, num_weekdays))

    def _generate_vacation_weeks(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        Generate evenly-distributed vacation weeks within the date range.

        Args:
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            List of week start dates (Mondays) that are vacation weeks
        """
        # Calculate total weeks in the range
        total_days = (end_date - start_date).days
        total_weeks = total_days // 7

        # Calculate number of vacation weeks based on the duration
        years = total_days / 365.25
        num_vacation_weeks = max(1, int(years * self.vacation_weeks_per_year))

        # Don't have more vacation weeks than total weeks
        num_vacation_weeks = min(num_vacation_weeks, total_weeks)

        if num_vacation_weeks == 0:
            return []

        # Generate all possible week starts (Mondays)
        possible_weeks = []
        current = self._get_week_start(start_date)
        while current <= end_date:
            # Avoid vacation weeks during major holiday periods (they're already low activity)
            # Skip weeks containing Christmas or New Year
            week_end = current + timedelta(days=6)
            is_holiday_week = False
            check_date = current
            while check_date <= week_end:
                if self._is_holiday(check_date):
                    # Check if it's a major holiday (Christmas, New Year's)
                    if check_date.month == 12 and check_date.day >= 20:
                        is_holiday_week = True
                        break
                    if check_date.month == 1 and check_date.day <= 7:
                        is_holiday_week = True
                        break
                check_date += timedelta(days=1)

            if not is_holiday_week:
                possible_weeks.append(current)
            current += timedelta(days=7)

        # Evenly distribute vacation weeks throughout the period
        if len(possible_weeks) <= num_vacation_weeks:
            return possible_weeks

        # Calculate interval to evenly space vacation weeks
        interval = len(possible_weeks) / num_vacation_weeks
        vacation_weeks = []
        for i in range(num_vacation_weeks):
            index = int(i * interval)
            # Add some randomness (+/- 1 week) to make it look more natural
            offset = random.randint(-1, 1)
            index = max(0, min(len(possible_weeks) - 1, index + offset))
            vacation_weeks.append(possible_weeks[index])

        return vacation_weeks

    def _calculate_commit_count(self, date: datetime) -> int:
        """
        Calculate number of commits for a given date based on weights.

        Args:
            date: The date to calculate commits for

        Returns:
            Number of commits to create for this date
        """
        # Vacation weeks have no commits
        if self._is_vacation_week(date):
            return 0

        # Check if we're in a new week and need to select new weekdays
        week_start = self._get_week_start(date)
        if week_start != self.current_week_start:
            self.current_week_start = week_start
            self.selected_weekdays = self._select_weekdays_for_week(week_start)

        base_count = random.randint(self.min_commits, self.max_commits)

        # Apply weights based on day type (priority order: holiday > weekend > weekday)
        if self._is_holiday(date):
            # Holidays reduce activity significantly
            probability = self.holiday_weight
        elif self._is_weekend(date):
            # Weekends can increase or decrease activity
            probability = self.weekend_weight
        else:
            # Weekdays: only selected weekdays get commits
            if date.weekday() not in self.selected_weekdays:
                return 0
            # Selected weekdays get full commits (no probability reduction)
            probability = 1.0

        # Use probability to potentially reduce commit count
        # For weights < 1.0, some days might have 0 commits
        if probability < 1.0 and random.random() > probability:
            return 0

        # For weights > 1.0, potentially add extra commits
        if probability > 1.0:
            extra_commits = int((probability - 1.0) * base_count)
            base_count += random.randint(0, extra_commits)

        return base_count

    def _generate_work_hours_time(self) -> time:
        """
        Generate a random time during work hours (9 AM - 6 PM).

        Returns:
            A random time object between 9:00 and 18:00
        """
        hour = random.randint(9, 17)  # 9 AM to 5 PM (hour 17 = 5:xx PM)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return time(hour, minute, second)

    def _create_commit(self, commit_datetime: datetime, dry_run: bool = False) -> None:
        """
        Create a single backdated commit.

        Args:
            commit_datetime: The datetime to backdate the commit to
            dry_run: If True, don't actually create the commit
        """
        if dry_run:
            return

        # Ensure activity.log exists
        if not self.activity_log_path.exists():
            self.activity_log_path.touch()

        # Append to activity log
        with open(self.activity_log_path, "a") as f:
            f.write(f"Activity logged at {commit_datetime.isoformat()}\n")

        # Stage the file
        self.repo.index.add([str(self.activity_log_path)])

        # Create commit with backdated timestamp
        commit_date_str = commit_datetime.strftime("%Y-%m-%d %H:%M:%S")
        self.repo.index.commit(
            "Activity log update",
            author_date=commit_date_str,
            commit_date=commit_date_str,
        )

    def generate_commits(
        self,
        start_date: str,
        end_date: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, datetime], None]] = None,
    ) -> List[datetime]:
        """
        Generate backdated commits across a date range.

        Args:
            start_date: Start date (ISO format or natural language)
            end_date: End date (ISO format or natural language)
            dry_run: If True, simulate without creating commits
            progress_callback: Optional callback function called after each commit
                              with (current_index, total_count, commit_datetime)

        Returns:
            List of commit datetimes that were (or would be) created
        """
        start = parser.parse(start_date)
        end = parser.parse(end_date)

        if start >= end:
            raise ValueError("Start date must be before end date")

        # Generate vacation weeks for this date range
        self.vacation_weeks = self._generate_vacation_weeks(start, end)

        commits_to_create: List[datetime] = []
        current_date = start

        # Iterate through each day in the range
        while current_date <= end:
            commit_count = self._calculate_commit_count(current_date)

            # Generate commits for this day
            for _ in range(commit_count):
                # Generate random time during work hours
                work_time = self._generate_work_hours_time()

                # Combine date with time
                commit_datetime = datetime.combine(current_date.date(), work_time)
                commits_to_create.append(commit_datetime)

            current_date += timedelta(days=1)

        # Sort commits chronologically
        commits_to_create.sort()

        # Create the commits
        total_commits = len(commits_to_create)
        for index, commit_datetime in enumerate(commits_to_create, 1):
            self._create_commit(commit_datetime, dry_run)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(index, total_commits, commit_datetime)

        return commits_to_create

    def clear_commits(self, dry_run: bool = False) -> int:
        """
        Remove all commits that only modified activity.log.

        This function identifies and removes commits where the only file
        changed was activity.log, effectively clearing all commits created
        by this tool.

        Args:
            dry_run: If True, simulate without actually removing commits

        Returns:
            Number of commits that were (or would be) removed
        """
        # Get all commits in the current branch
        commits_to_remove = []

        for commit in self.repo.iter_commits():
            # Check if this commit only modified activity.log
            if len(commit.parents) == 0:
                # First commit in repo, check if it only has activity.log
                files = list(commit.stats.files.keys())
            else:
                # Get the diff between this commit and its parent
                parent = commit.parents[0]
                files = list(commit.diff(parent))
                files = [f.a_path if f.a_path else f.b_path for f in files]

            # Check if only activity.log was modified
            if len(files) == 1 and files[0] == "activity.log":
                commits_to_remove.append(commit)

        if not commits_to_remove:
            return 0

        if dry_run:
            return len(commits_to_remove)

        # Find the commit to reset to (the first commit that's not being removed)
        # We need to go through commits in reverse order (oldest to newest)
        all_commits = list(self.repo.iter_commits())
        all_commits.reverse()

        reset_to_commit = None
        for commit in all_commits:
            if commit not in commits_to_remove:
                reset_to_commit = commit
                break

        # If all commits are activity.log commits, we need to clear everything
        if reset_to_commit is None:
            # Reset to remove all commits (creates a new branch with no history)
            self.repo.git.update_ref('-d', 'HEAD')
            self.repo.index.remove(['activity.log'], working_tree=True)
            if self.activity_log_path.exists():
                self.activity_log_path.unlink()
        else:
            # Reset to the commit before the activity commits
            self.repo.git.reset('--hard', reset_to_commit.hexsha)

        return len(commits_to_remove)
