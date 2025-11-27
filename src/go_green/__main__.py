"""Entry point for the Go Green CLI."""

from .cli import app


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
