
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


# Project root: the directory containing this script
PROJECT_ROOT = Path(__file__).resolve().parent

# Save the ZIP outside the project directory
OUTPUT_FILE = PROJECT_ROOT.parent / "medstock_source.zip"


# Directories to exclude
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "node_modules",
    "build",
    "dist",
}

# Individual files to exclude
EXCLUDED_FILES = {
    ".env",
}

# File extensions to exclude
EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
}

# Database temporary files
EXCLUDED_SUFFIXES = (
    "-wal",
    "-shm",
)


def should_exclude(path: Path) -> bool:
    """Determine whether a file or directory should be excluded."""

    relative_path = path.relative_to(PROJECT_ROOT)

    # Exclude any path containing a prohibited directory
    if any(part in EXCLUDED_DIRS for part in relative_path.parts):
        return True

    filename = path.name.lower()

    # Exclude environment files such as .env and .env.local
    if filename == ".env" or filename.startswith(".env."):
        return True

    if filename in EXCLUDED_FILES:
        return True

    # Exclude compiled, database and private-key files
    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True

    # Exclude SQLite WAL and SHM files
    if filename.endswith(EXCLUDED_SUFFIXES):
        return True

    return False


def create_zip() -> None:
    """Create a compressed ZIP archive of the MEDSTOCK project."""

    included_count = 0
    excluded_count = 0

    print(f"Project: {PROJECT_ROOT}")
    print(f"Output:  {OUTPUT_FILE}")
    print("\nPackaging project...\n")

    with ZipFile(
        OUTPUT_FILE,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:

        for path in PROJECT_ROOT.rglob("*"):

            if path.is_symlink():
                excluded_count += 1
                continue

            if path.is_dir():
                continue

            if should_exclude(path):
                excluded_count += 1
                continue

            archive_name = path.relative_to(PROJECT_ROOT)

            archive.write(path, archive_name)
            included_count += 1

            print(f"Added: {archive_name}")

    print("\nPackaging complete!")
    print(f"Files included: {included_count}")
    print(f"Files excluded: {excluded_count}")
    print(f"ZIP location: {OUTPUT_FILE}")
    print(f"ZIP size: {OUTPUT_FILE.stat().st_size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    create_zip()
