#!/usr/bin/env python3
"""Set up jDocMunch MCP for section-level access to medical datasets.

After downloading datasets with datasets.py, this script:
  1. Indexes every dataset directory into jDocMunch
  2. Generates MCP server config for Claude Code / Claude Desktop
  3. Outputs token-savings estimates

This replaces full-file reads with O(1) byte-offset section retrieval,
cutting token usage by 10-50x when querying the knowledge base.

Usage:
    # First, download datasets
    python examples/medical_tutor/datasets.py all

    # Then index them into jDocMunch
    python examples/medical_tutor/setup_jdocmunch.py

    # Or point to custom data dir
    python examples/medical_tutor/setup_jdocmunch.py --data-dir /path/to/data

    # Generate MCP config only (no indexing)
    python examples/medical_tutor/setup_jdocmunch.py --config-only
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path.home() / ".openjarvis" / "medical_data"

# Dataset directories and their labels for jDocMunch indexing
DATASET_DIRS = {
    "pubmed_oa":  "PubMed Open Access articles",
    "medmcqa":    "MedMCQA exam questions",
    "mimic":      "MIMIC-IV clinical notes",
    "pubmedqa":   "PubMedQA evidence reasoning",
}


def check_jdocmunch_installed() -> bool:
    """Check if jdocmunch-mcp is installed."""
    return shutil.which("jdocmunch-mcp") is not None


def install_jdocmunch() -> bool:
    """Install jdocmunch-mcp via pip."""
    print("Installing jdocmunch-mcp...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "jdocmunch-mcp"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("  Installed successfully.")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"  Install failed: {exc.stderr}", file=sys.stderr)
        return False


def index_directory(data_path: Path, label: str) -> Dict[str, Any]:
    """Index a local directory into jDocMunch."""
    result = {"path": str(data_path), "label": label, "indexed": False, "error": None}

    if not data_path.exists():
        result["error"] = "directory not found"
        return result

    # Count files
    files = list(data_path.rglob("*.txt")) + list(data_path.rglob("*.jsonl"))
    if not files:
        result["error"] = "no indexable files found"
        return result

    result["file_count"] = len(files)
    print(f"  Indexing {len(files)} files from {data_path.name}...")

    try:
        # jDocMunch index_local command
        proc = subprocess.run(
            ["jdocmunch-mcp", "index-local", str(data_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode == 0:
            result["indexed"] = True
            print(f"  Indexed: {label}")
        else:
            # Try via Python module as fallback
            proc2 = subprocess.run(
                [sys.executable, "-m", "jdocmunch_mcp", "index-local", str(data_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc2.returncode == 0:
                result["indexed"] = True
                print(f"  Indexed: {label}")
            else:
                result["error"] = proc.stderr or proc2.stderr or "indexing failed"
                print(f"  Warning: {result['error']}")

    except FileNotFoundError:
        result["error"] = "jdocmunch-mcp command not found"
    except subprocess.TimeoutExpired:
        result["error"] = "indexing timed out (>5 min)"
    except Exception as exc:
        result["error"] = str(exc)

    return result


def generate_mcp_config(
    data_dir: Path,
    output_path: Path | None = None,
) -> Dict[str, Any]:
    """Generate MCP server configuration for Claude Code / Claude Desktop.

    Returns the config dict and optionally writes it to a file.
    """
    config = {
        "mcpServers": {
            "jdocmunch": {
                "command": "uvx",
                "args": ["jdocmunch-mcp"],
                "env": {
                    "DOC_INDEX_PATH": str(Path.home() / ".doc-index"),
                },
            }
        }
    }

    # Add API key env vars if they exist
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(key)
        if val:
            config["mcpServers"]["jdocmunch"]["env"][key] = val

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n  MCP config written to: {output_path}")

    return config


def generate_claude_code_settings(data_dir: Path) -> Dict[str, Any]:
    """Generate .mcp.json for Claude Code project-level MCP config."""
    config = {
        "mcpServers": {
            "jdocmunch": {
                "command": "uvx",
                "args": ["jdocmunch-mcp"],
                "env": {
                    "DOC_INDEX_PATH": str(Path.home() / ".doc-index"),
                },
            }
        }
    }

    for key in ("ANTHROPIC_API_KEY",):
        val = os.environ.get(key)
        if val:
            config["mcpServers"]["jdocmunch"]["env"][key] = val

    return config


def print_usage_guide(data_dir: Path) -> None:
    """Print how to use jDocMunch with the indexed medical data."""
    print()
    print("=" * 60)
    print("  jDocMunch — Token-Efficient Medical Data Access")
    print("=" * 60)
    print()
    print("  Instead of loading entire files (~12k tokens each),")
    print("  jDocMunch retrieves individual sections (~400 tokens).")
    print()
    print("  MCP Tools available in Claude Code / Claude Desktop:")
    print()
    print("    search_sections  — Find sections by keyword")
    print("      e.g. search_sections('heart failure pathophysiology')")
    print()
    print("    get_toc          — List all sections in a document")
    print("      e.g. get_toc('pubmed_oa')")
    print()
    print("    get_section      — Retrieve one section by ID")
    print("      e.g. get_section('pubmed_oa::PMC1234::abstract#2')")
    print()
    print("    get_sections     — Batch retrieve multiple sections")
    print()
    print("    get_section_context — Section + parent + sibling summaries")
    print()
    print("  Estimated token savings per query:")
    print("    Single section lookup:    ~400 tokens  (vs ~12,000)")
    print("    Browse dataset structure: ~800 tokens  (vs ~40,000)")
    print("    Full dataset exploration: ~2,000 tokens (vs ~100,000)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up jDocMunch MCP for section-level medical data access",
    )
    parser.add_argument(
        "--data-dir", type=str, default=str(DATA_DIR),
        help=f"Medical data directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--config-only", action="store_true",
        help="Only generate MCP config, skip indexing",
    )
    parser.add_argument(
        "--install", action="store_true",
        help="Install jdocmunch-mcp if not present",
    )
    parser.add_argument(
        "--claude-desktop", action="store_true",
        help="Write Claude Desktop config to ~/Library/Application Support/Claude/",
    )

    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    print("=" * 60)
    print("  jDocMunch MCP Setup for Medical Datasets")
    print("=" * 60)
    print()

    # Step 1: Check / install jDocMunch
    if not check_jdocmunch_installed():
        if args.install:
            if not install_jdocmunch():
                print("\n  Failed to install. Try manually:")
                print("    pip install jdocmunch-mcp")
                sys.exit(1)
        else:
            print("  jdocmunch-mcp not found. Install with:")
            print("    pip install jdocmunch-mcp")
            print("  Or re-run with --install")
            print()

    # Step 2: Index datasets
    if not args.config_only:
        print("Indexing medical datasets into jDocMunch...")
        print("-" * 40)

        results: List[Dict[str, Any]] = []
        for dirname, label in DATASET_DIRS.items():
            dir_path = data_dir / dirname
            if dir_path.exists():
                result = index_directory(dir_path, label)
                results.append(result)
            else:
                print(f"  Skipping {dirname} (not downloaded yet)")

        # Also index any curriculum data
        curriculum_dir = Path("./curriculum")
        if curriculum_dir.exists():
            result = index_directory(curriculum_dir, "Open RN / UMich curriculum")
            results.append(result)

        print()
        indexed = sum(1 for r in results if r.get("indexed"))
        total_files = sum(r.get("file_count", 0) for r in results)
        print(f"  Indexed: {indexed}/{len(results)} datasets ({total_files} files)")

        for r in results:
            if r.get("error"):
                print(f"  Warning: {r['label']}: {r['error']}")

    # Step 3: Generate MCP configs
    print()
    print("MCP Configuration")
    print("-" * 40)

    # Project-level .mcp.json for Claude Code
    project_root = Path(__file__).resolve().parent.parent.parent
    mcp_json_path = project_root / ".mcp.json"

    cc_config = generate_claude_code_settings(data_dir)

    # Merge with existing .mcp.json if present
    if mcp_json_path.exists():
        try:
            with open(mcp_json_path) as f:
                existing = json.load(f)
            existing.setdefault("mcpServers", {})
            existing["mcpServers"]["jdocmunch"] = cc_config["mcpServers"]["jdocmunch"]
            cc_config = existing
        except (json.JSONDecodeError, KeyError):
            pass

    with open(mcp_json_path, "w") as f:
        json.dump(cc_config, f, indent=2)
    print(f"  Claude Code config: {mcp_json_path}")

    # Claude Desktop config (optional)
    if args.claude_desktop:
        desktop_paths = [
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            Path.home() / ".config" / "claude" / "claude_desktop_config.json",
        ]
        for dp in desktop_paths:
            if dp.parent.exists():
                generate_mcp_config(data_dir, dp)
                break

    # Print the config for manual use
    print()
    print("  Add to your MCP client config:")
    print()
    print(json.dumps(cc_config, indent=2))

    print_usage_guide(data_dir)


if __name__ == "__main__":
    main()
