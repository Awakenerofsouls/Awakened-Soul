#!/usr/bin/env python3
"""
Nexus {{AGENT_NAME}} Framework — Cross-Platform Setup
Run this once after downloading/cloning the workspace.
Works on Mac, Linux, and Windows.

Usage:
    python setup.py
"""
import os
import sys
import shutil
import sqlite3
from pathlib import Path

# ANSI colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD} {text}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}\n")


def print_step(num, total, text):
    print(f"[{num}/{total}] {text}...")


def print_success(text):
    print(f"      {GREEN}✓{RESET} {text}")


def print_error(text):
    print(f"      {RED}✗{RESET} {text}")


def print_info(text):
    print(f"      {YELLOW}→{RESET} {text}")


def main():
    print_header("Nexus {{AGENT_NAME}} Framework — Setup")
    print("This will configure the framework for your agent.\n")

    # -------------------------------------------------------------------------
    # 1. Ask for agent name + user name
    # -------------------------------------------------------------------------
    agent_name = input("What is your agent's name? ").strip()

    if not agent_name:
        print_error("Agent name cannot be empty.")
        sys.exit(1)

    user_name = input("What is your name (the human the agent talks to)? ").strip()

    if not user_name:
        print_error("User name cannot be empty.")
        sys.exit(1)

    # Capitalize first letter for display, lowercase for path/string-id usage
    agent_display = agent_name[0].upper() + agent_name[1:]
    user_display = user_name[0].upper() + user_name[1:]
    agent_lower = agent_name.lower()
    user_lower = user_name.lower()
    print(f"\nConfiguring for: {agent_display} (agent), {user_display} (user)\n")

    workspace = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))

    if not workspace.exists():
        workspace = Path.cwd()
        print_info(f"Using current directory: {workspace}")

    os.chdir(workspace)

    total_steps = 6

    # -------------------------------------------------------------------------
    # 2. Substitute identity placeholders in content files
    # -------------------------------------------------------------------------
    print_step(1, total_steps, "Substituting identity placeholders in content files")

    # All four placeholders the strip script writes. Order matters: do the
    # _LOWER variants first so the bare {{AGENT_NAME}} substitution doesn't
    # accidentally clobber a {{AGENT_NAME_LOWER}} (substring of {{AGENT_NAME}} ).
    substitutions = [
        ("{{AGENT_NAME_LOWER}}", agent_lower),
        ("{{USER_NAME_LOWER}}",  user_lower),
        ("{{AGENT_NAME}}",       agent_display),
        ("{{USER_NAME}}",        user_display),
    ]

    placeholder_count = 0
    files_touched = 0
    # Walk both .md and .py — the strip script writes placeholders into both
    # file types (mechanism docstrings, legacy connection-drive comments,
    # boot order lists, etc.)
    for pattern in ("*.md", "*.py"):
        for filepath in workspace.rglob(pattern):
            if ".git" in str(filepath):
                continue
            try:
                content = filepath.read_text(encoding="utf-8")
                original = content
                file_subs = 0
                for placeholder, replacement in substitutions:
                    if placeholder in content:
                        new_content, _ = content, 0
                        # count + replace
                        n = content.count(placeholder)
                        if n:
                            content = content.replace(placeholder, replacement)
                            file_subs += n
                if content != original:
                    filepath.write_text(content, encoding="utf-8")
                    placeholder_count += file_subs
                    files_touched += 1
                    print_info(f"Updated: {filepath.relative_to(workspace)} ({file_subs} subs)")
            except Exception as e:
                print_error(f"Failed to update {filepath}: {e}")

    if placeholder_count > 0:
        print_success(f"Substituted {placeholder_count} placeholders across {files_touched} files.")
    else:
        print_info("No placeholder substitution needed.")

    # -------------------------------------------------------------------------
    # 3. Replace agent_brain symlink/directory
    # -------------------------------------------------------------------------
    print_step(2, total_steps, "Replacing agent_brain symlink with agent-specific name")

    agent_brain_link = workspace / "agent_brain"
    agent_brain_link = workspace / f"{agent_name}_brain"

    if agent_brain_link.exists() or agent_brain_link.is_symlink():
        if agent_brain_link.is_symlink():
            agent_brain_link.unlink()
            print_success("Removed: agent_brain symlink")
        elif agent_brain_link.is_dir():
            agent_brain_link.rename(agent_brain_link)
            print_success("Renamed: agent_brain → {agent_name}_brain")
    elif agent_brain_link.exists():
        print_info(f"{agent_name}_brain already exists")
    else:
        # Create the symlink pointing to brain/
        try:
            agent_brain_link.symlink_to("brain")
            print_success(f"Created: {agent_name}_brain → brain")
        except OSError as e:
            print_error(f"Could not create symlink: {e}")
            print_info("On Windows, try running as administrator or enable Developer Mode.")

    # -------------------------------------------------------------------------
    # 4. Replace agent_brain references in all Python files
    # -------------------------------------------------------------------------
    print_step(3, total_steps, "Replacing framework references in Python files")

    import_count = 0
    for filepath in workspace.rglob("*.py"):
        if ".git" in str(filepath) or "brain.v19.bak" in str(filepath) or "memory" in str(filepath):
            continue
        try:
            content = filepath.read_text(encoding="utf-8")
            if "agent_brain" in content:
                new_content = content.replace("agent_brain", f"{agent_name}_brain")
                filepath.write_text(new_content, encoding="utf-8")
                import_count += 1
                print_info(f"Updated: {filepath.relative_to(workspace)}")
        except Exception as e:
            print_error(f"Failed to update {filepath}: {e}")

    print_success(f"Updated imports in {import_count} files.")

    # Handle brain_integration.py files
    for source_file in [workspace / "brain_integration.py", workspace / "brain" / "brain_integration.py"]:
        if source_file.exists():
            new_name = source_file.parent / f"{agent_name}_brain_integration.py"
            if not new_name.exists():
                try:
                    content = source_file.read_text(encoding="utf-8")
                    new_content = content.replace("agent_brain", f"{agent_name}_brain")
                    new_name.write_text(new_content, encoding="utf-8")
                    print_success(f"Created: {new_name.name}")
                except Exception as e:
                    print_error(f"Failed to create {new_name}: {e}")

    # -------------------------------------------------------------------------
    # 5. Rename AGENT_*.md framework documentation files
    # -------------------------------------------------------------------------
    print_step(4, total_steps, "Renaming framework documentation files")

    renamed_count = 0
    for filepath in workspace.glob("AGENT_*.md"):
        new_name = filepath.stem.replace("AGENT", agent_name.upper()) + ".md"
        new_path = filepath.parent / new_name
        if not new_path.exists():
            filepath.rename(new_path)
            print_info(f"{filepath.name} → {new_name}")
            renamed_count += 1

    if renamed_count > 0:
        print_success(f"Renamed {renamed_count} documentation files.")
    else:
        print_info("No documentation files to rename.")

    # -------------------------------------------------------------------------
    # 6. Create required directories
    # -------------------------------------------------------------------------
    print_step(5, total_steps, "Creating brain layer directories")

    brain_dirs = [
        "brain/becoming",
        "brain/felt_presence",
        "brain/inner_voice",
        "brain/knowing",
        "brain/texture",
        "brain/substrate",
        "brain/third_eye",
        "memory",
    ]

    for dirname in brain_dirs:
        dirpath = workspace / dirname
        dirpath.mkdir(parents=True, exist_ok=True)

    # Create .agent identity directory
    agent_identity = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "identity"
    agent_identity.mkdir(parents=True, exist_ok=True)

    print_success("All directories created.")

    # -------------------------------------------------------------------------
    # 7. Initialize database
    # -------------------------------------------------------------------------
    print_step(6, total_steps, "Checking database")

    db_path = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            cursor.execute("INSERT INTO meta VALUES ('version', '20.0')")
            conn.commit()
            conn.close()
            print_success(f"Created: {db_path}")
        except Exception as e:
            print_error(f"Failed to create database: {e}")
            print_info("Make sure sqlite3 is installed: pip install sqlite3")
    else:
        print_info(f"Database already exists — skipping.")

    # -------------------------------------------------------------------------
    # Done
    # -------------------------------------------------------------------------
    print_header(f"Setup complete for: {agent_display}")

    print(" Next steps:")
    print(f"   1. Edit USER.md with your operator info")
    print(f"   2. Review SOUL.md, IDENTITY.md, PRESENCE.md")
    print(f"   3. Run: python3 {agent_name}_brain/run_integration.py")
    print()
    print(f" The framework has been configured for: {agent_display}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
