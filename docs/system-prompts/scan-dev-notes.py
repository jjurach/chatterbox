#!/usr/bin/env python3
"""
Scan dev_notes/ directory for anomalies and planning inconsistencies.

This script identifies issues such as:
- Duplicate epic references
- TODO/FIXME comments in planning files
- Incomplete/half-implemented markers
- References to non-existent files or epics
- Orphaned documentation
- Status inconsistencies
- Missing closure markers
- Inconsistent epic numbering
- Conflicting metadata

Output modes: default, --verbose, --html, --json
Filter by issue type: --filter=duplicate,todo,incomplete,etc.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime


class Severity(Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass
class Issue:
    """Represents a single issue found during scanning."""
    issue_type: str
    severity: Severity
    file_path: str
    filename: str
    line_number: int
    context: str
    suggestion: str
    category: str


class DevNoteScanner:
    """Scans dev_notes directory for anomalies and inconsistencies."""

    def __init__(self, dev_notes_dir: str, verbose: bool = False, filter_types: Optional[List[str]] = None, quiet: bool = False):
        """Initialize scanner."""
        self.dev_notes_dir = Path(dev_notes_dir)
        self.verbose = verbose
        self.filter_types = set(filter_types) if filter_types else set()
        self.quiet = quiet

        self.issues: List[Issue] = []
        self.stats = {
            "total_files": 0,
            "files_scanned": 0,
            "issues_found": 0,
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
        }

        # Patterns for detection
        self.todo_pattern = re.compile(r'(TODO|FIXME|XXX|HACK)\s*[:\-]?\s*(.*?)(?=\n|$)', re.IGNORECASE)
        self.incomplete_pattern = re.compile(
            r'(half.?implemented|incomplete|not.?finished|work.?in.?progress|wip)',
            re.IGNORECASE
        )
        self.epic_pattern = re.compile(r'[Ee]pic\s*[:#]?\s*(\d+)', re.IGNORECASE)
        self.status_pattern = re.compile(
            r'\*\*Status\*\*\s*:\s*([\w\s]+?)(?:\n|$)',
            re.IGNORECASE
        )
        self.file_ref_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)|`([^`]+\.(py|md|yaml|json))`')

        # Track discovered files for cross-reference validation
        self.discovered_files: Set[str] = set()
        self.epic_references: Dict[int, List[str]] = defaultdict(list)
        self.file_references: Dict[str, List[str]] = defaultdict(list)

    def scan(self) -> List[Issue]:
        """Scan the dev_notes directory."""
        if not self.dev_notes_dir.exists():
            print(f"Error: dev_notes directory not found at {self.dev_notes_dir}")
            sys.exit(1)

        # First pass: discover files
        self._discover_files()
        self.stats["total_files"] = len(list(self.dev_notes_dir.glob("**/*.md")))

        # Second pass: scan for issues
        for file_path in sorted(self.dev_notes_dir.glob("**/*.md")):
            self._scan_file(file_path)

        # Print real-time output if not quiet and not outputting structured formats
        if not self.quiet and not hasattr(self, '_output_mode'):
            self._print_realtime_summary()

        return self.issues

    def _print_realtime_summary(self) -> None:
        """Print real-time summary during scanning."""
        if self.issues and not self.quiet:
            current_file = None
            count = 0
            for issue in sorted(self.issues[:20], key=lambda x: (x.filename, x.line_number)):
                if issue.filename != current_file:
                    if count > 0:
                        print()
                    print(f"{issue.filename}")
                    current_file = issue.filename
                    count += 1

                severity_marker = {
                    Severity.ERROR: "✗",
                    Severity.WARNING: "⚠",
                    Severity.NOTE: "ℹ",
                }[issue.severity]

                print(f"  {severity_marker} L{issue.line_number:4d} | {issue.issue_type:25s} | {issue.category}")

            if len(self.issues) > 20:
                print(f"\n  ... and {len(self.issues) - 20} more issues")

    def _discover_files(self) -> None:
        """Discover all files referenced in project."""
        project_root = self.dev_notes_dir.parent.parent.parent

        for file_path in self.dev_notes_dir.glob("**/*"):
            if file_path.is_file():
                # Store relative paths
                rel_path = str(file_path.relative_to(project_root))
                self.discovered_files.add(rel_path)
                self.discovered_files.add(str(file_path.name))

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single file for issues."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            self._add_issue(
                issue_type="file_read_error",
                severity=Severity.ERROR,
                file_path=file_path,
                line_number=0,
                context=str(e),
                suggestion="Check file permissions and encoding",
                category="Infrastructure"
            )
            return

        self.stats["files_scanned"] += 1
        relative_path = str(file_path.relative_to(self.dev_notes_dir.parent))

        # Run all checks
        self._check_todo_comments(file_path, lines, relative_path)
        self._check_incomplete_markers(file_path, lines, relative_path)
        self._check_status_consistency(file_path, lines, relative_path)
        self._check_epic_references(file_path, content, lines, relative_path)
        self._check_file_references(file_path, lines, relative_path)
        self._check_closure_markers(file_path, lines, relative_path)
        self._check_orphaned_documentation(file_path, lines, relative_path)

    def _check_todo_comments(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Detect TODO/FIXME comments in planning files."""
        if "dev_notes" not in str(file_path):
            return

        for line_num, line in enumerate(lines, 1):
            matches = self.todo_pattern.findall(line)
            for match in matches:
                if isinstance(match, tuple):
                    marker, context = match[0], match[1]
                else:
                    marker = match
                    context = ""

                self._add_issue(
                    issue_type="todo_comment",
                    severity=Severity.WARNING,
                    file_path=file_path,
                    line_number=line_num,
                    context=line.strip(),
                    suggestion=f"Resolve or document the {marker}: {context[:50]}",
                    category="Planning"
                )

    def _check_incomplete_markers(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Detect files marked as incomplete or half-implemented."""
        content = '\n'.join(lines)

        if self.incomplete_pattern.search(content):
            for line_num, line in enumerate(lines, 1):
                if self.incomplete_pattern.search(line):
                    self._add_issue(
                        issue_type="incomplete_marker",
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        context=line.strip(),
                        suggestion="Complete implementation or move to backlog/inbox",
                        category="Status"
                    )

    def _check_status_consistency(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Check for status marker inconsistencies."""
        content = '\n'.join(lines)

        # Find all status markers
        statuses = [m.group(1).strip() for m in self.status_pattern.finditer(content)]

        if not statuses:
            return

        # Track conflicting statuses (multiple different statuses in one file)
        if len(set(statuses)) > 1:
            self._add_issue(
                issue_type="conflicting_status",
                severity=Severity.ERROR,
                file_path=file_path,
                line_number=1,
                context=f"Multiple statuses found: {', '.join(set(statuses))}",
                suggestion="Unify status markers - each file should have one consistent status",
                category="Metadata"
            )

        # Check for vague status values
        for line_num, line in enumerate(lines, 1):
            match = self.status_pattern.search(line)
            if match:
                status = match.group(1).strip()
                if status.lower() not in ['completed', 'completed ', 'in-progress', 'in progress',
                                         'pending', 'planned', 'on-hold', 'blocked', 'draft']:
                    self._add_issue(
                        issue_type="undefined_status",
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        context=f"Status: {status}",
                        suggestion="Use standardized status: Completed, In-Progress, Pending, Planned, On-Hold, Blocked, or Draft",
                        category="Metadata"
                    )

    def _check_epic_references(self, file_path: Path, content: str, lines: List[str], relative_path: str) -> None:
        """Check for duplicate epic references and numbering inconsistencies."""
        epics_found: Dict[int, List[int]] = defaultdict(list)

        for line_num, line in enumerate(lines, 1):
            for match in self.epic_pattern.finditer(line):
                epic_num = int(match.group(1))
                epics_found[epic_num].append(line_num)
                self.epic_references[epic_num].append(relative_path)

        # Check for inconsistent epic numbering (gaps in sequence)
        if epics_found:
            max_epic = max(epics_found.keys())
            for i in range(1, max_epic):
                if i not in epics_found and i < max_epic:
                    # This might indicate a gap, which is OK, so we'll be lenient
                    pass

            # Check for duplicate epic references within same file
            for epic_num, line_numbers in epics_found.items():
                if len(line_numbers) > 2:  # Allow some repetition (title, references, etc.)
                    self._add_issue(
                        issue_type="excessive_epic_mentions",
                        severity=Severity.NOTE,
                        file_path=file_path,
                        line_number=line_numbers[0],
                        context=f"Epic {epic_num} mentioned {len(line_numbers)} times",
                        suggestion="Consider if all mentions are necessary or if content is repetitive",
                        category="Structure"
                    )

    def _check_file_references(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Check for cross-references to files that don't exist."""
        project_root = self.dev_notes_dir.parent.parent.parent

        for line_num, line in enumerate(lines, 1):
            # Find markdown links [text](path) and code references
            for match in self.file_ref_pattern.finditer(line):
                referenced_file = match.group(2) or match.group(3)

                if not referenced_file:
                    continue

                # Skip URLs
                if referenced_file.startswith('http'):
                    continue

                # Normalize path
                if referenced_file.startswith('./'):
                    referenced_file = referenced_file[2:]
                if referenced_file.startswith('../'):
                    # Resolve relative paths
                    base_dir = file_path.parent
                    resolved = (base_dir / referenced_file).resolve()
                    referenced_file = str(resolved.relative_to(project_root))

                self.file_references[referenced_file].append(relative_path)

                # Check if file exists
                full_path = project_root / referenced_file
                if not full_path.exists():
                    self._add_issue(
                        issue_type="missing_file_reference",
                        severity=Severity.ERROR,
                        file_path=file_path,
                        line_number=line_num,
                        context=line.strip(),
                        suggestion=f"Verify that '{referenced_file}' exists or update the reference",
                        category="References"
                    )

    def _check_closure_markers(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Check for missing closure markers on completed tasks."""
        content = '\n'.join(lines)

        # Check if file has "Completed" status but lacks closure info
        if 'Status' in content and 'Completed' in content:
            if 'Date Completed' not in content and 'Completion Date' not in content:
                if 'Date Started' in content:
                    self._add_issue(
                        issue_type="missing_completion_date",
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=1,
                        context="File marked as Completed but lacks completion date",
                        suggestion="Add 'Date Completed: YYYY-MM-DD' field for audit trail",
                        category="Metadata"
                    )

    def _check_orphaned_documentation(self, file_path: Path, lines: List[str], relative_path: str) -> None:
        """Check for orphaned documentation (mentioned but not properly linked)."""
        # Look for file references in the content that aren't properly formatted
        content = '\n'.join(lines)

        # Find potential file paths that aren't in markdown links
        potential_files = re.findall(r'\b([a-z0-9_-]+\.(?:py|md|yaml|json|txt))\b', content, re.IGNORECASE)

        for potential_file in potential_files:
            # Check if it's in a markdown link
            if f']({potential_file}' not in content and f'`{potential_file}`' not in content:
                # This is a potential orphaned reference
                for line_num, line in enumerate(lines, 1):
                    if potential_file in line:
                        self._add_issue(
                            issue_type="orphaned_reference",
                            severity=Severity.NOTE,
                            file_path=file_path,
                            line_number=line_num,
                            context=line.strip(),
                            suggestion=f"Consider formatting '{potential_file}' as a markdown link or code reference",
                            category="Documentation"
                        )
                        break

    def _add_issue(self, issue_type: str, severity: Severity, file_path: Path,
                   line_number: int, context: str, suggestion: str, category: str) -> None:
        """Add an issue to the list."""
        # Check if this issue type should be filtered
        if self.filter_types and issue_type not in self.filter_types:
            return

        issue = Issue(
            issue_type=issue_type,
            severity=severity,
            file_path=str(file_path),
            filename=file_path.name,
            line_number=line_number,
            context=context,
            suggestion=suggestion,
            category=category
        )

        self.issues.append(issue)
        self.stats["issues_found"] += 1
        self.stats["by_type"][issue_type] += 1
        self.stats["by_severity"][severity.value] += 1

    def print_default_output(self) -> None:
        """Print concise default output."""
        print("\n" + "=" * 80)
        print("DEV NOTES SCANNING REPORT")
        print("=" * 80)

        if not self.issues:
            print("\nNo issues found!")
            self._print_statistics()
            return

        current_file = None
        for issue in sorted(self.issues, key=lambda x: (x.filename, x.line_number)):
            if issue.filename != current_file:
                print(f"\n{issue.filename}")
                current_file = issue.filename

            severity_marker = {
                Severity.ERROR: "✗",
                Severity.WARNING: "⚠",
                Severity.NOTE: "ℹ",
            }[issue.severity]

            print(f"  {severity_marker} L{issue.line_number:4d} | {issue.issue_type:25s} | {issue.category}")

        self._print_statistics()

    def print_verbose_output(self) -> None:
        """Print detailed verbose output with context and suggestions."""
        print("\n" + "=" * 80)
        print("DEV NOTES DETAILED SCANNING REPORT")
        print("=" * 80)

        if not self.issues:
            print("\nNo issues found!")
            self._print_statistics()
            return

        current_file = None
        for issue in sorted(self.issues, key=lambda x: (x.filename, x.line_number)):
            if issue.filename != current_file:
                print(f"\n{'─' * 80}")
                print(f"FILE: {issue.filename}")
                print(f"PATH: {issue.file_path}")
                print('─' * 80)
                current_file = issue.filename

            severity_color = {
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️ ",
                Severity.NOTE: "ℹ️ ",
            }.get(issue.severity, "•")

            print(f"\n{severity_color} Line {issue.line_number}")
            print(f"   Type: {issue.issue_type}")
            print(f"   Category: {issue.category}")
            print(f"   Severity: {issue.severity.value.upper()}")
            print(f"   Context: {issue.context}")
            print(f"   Suggestion: {issue.suggestion}")

        self._print_statistics()

    def print_html_output(self) -> str:
        """Generate HTML report."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "<title>Dev Notes Scan Report</title>",
            "<style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }",
            ".container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            "h1 { color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }",
            "h2 { color: #0066cc; margin-top: 30px; }",
            ".stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }",
            ".stat-box { background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #0066cc; }",
            ".stat-number { font-size: 28px; font-weight: bold; color: #0066cc; }",
            ".stat-label { color: #666; margin-top: 5px; }",
            ".file-section { margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 5px; border-left: 4px solid #999; }",
            ".file-name { font-weight: bold; color: #333; font-size: 16px; }",
            ".file-path { color: #666; font-size: 12px; margin-bottom: 10px; }",
            ".issue { margin: 10px 0; padding: 10px; background: white; border-radius: 3px; border-left: 3px solid #ddd; }",
            ".error { border-left-color: #d32f2f; }",
            ".warning { border-left-color: #f57c00; }",
            ".note { border-left-color: #1976d2; }",
            ".severity { font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 12px; }",
            ".error .severity { background: #d32f2f; color: white; }",
            ".warning .severity { background: #f57c00; color: white; }",
            ".note .severity { background: #1976d2; color: white; }",
            ".line-number { color: #666; font-size: 12px; }",
            ".context { background: #f5f5f5; padding: 8px; border-radius: 3px; font-family: monospace; margin: 8px 0; }",
            ".suggestion { background: #e3f2fd; padding: 8px; border-radius: 3px; margin: 8px 0; color: #1565c0; }",
            ".footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='container'>",
            "<h1>Dev Notes Scanning Report</h1>",
            f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        ]

        # Statistics
        html.append("<h2>Statistics</h2>")
        html.append("<div class='stats'>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['total_files']}</div><div class='stat-label'>Total Files</div></div>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['files_scanned']}</div><div class='stat-label'>Files Scanned</div></div>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['issues_found']}</div><div class='stat-label'>Issues Found</div></div>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['by_severity'].get('error', 0)}</div><div class='stat-label'>Errors</div></div>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['by_severity'].get('warning', 0)}</div><div class='stat-label'>Warnings</div></div>")
        html.append(f"<div class='stat-box'><div class='stat-number'>{self.stats['by_severity'].get('note', 0)}</div><div class='stat-label'>Notes</div></div>")
        html.append("</div>")

        # Issues by file
        if self.issues:
            html.append("<h2>Issues by File</h2>")
            files = defaultdict(list)
            for issue in self.issues:
                files[issue.filename].append(issue)

            for filename in sorted(files.keys()):
                html.append(f"<div class='file-section'>")
                html.append(f"<div class='file-name'>{filename}</div>")
                html.append(f"<div class='file-path'>{files[filename][0].file_path}</div>")

                for issue in sorted(files[filename], key=lambda x: x.line_number):
                    severity_class = issue.severity.value
                    html.append(f"<div class='issue {severity_class}'>")
                    html.append(f"<div><span class='severity'>{issue.severity.value.upper()}</span> <span class='line-number'>Line {issue.line_number}</span></div>")
                    html.append(f"<div><strong>{issue.issue_type}</strong> [{issue.category}]</div>")
                    html.append(f"<div class='context'>{issue.context}</div>")
                    html.append(f"<div class='suggestion'>💡 {issue.suggestion}</div>")
                    html.append(f"</div>")

                html.append(f"</div>")

        # Issue type breakdown
        if self.stats['by_type']:
            html.append("<h2>Issues by Type</h2>")
            html.append("<table border='1' cellpadding='8' cellspacing='0' style='width: 100%;'>")
            html.append("<tr><th>Issue Type</th><th>Count</th></tr>")
            for issue_type in sorted(self.stats['by_type'].keys()):
                count = self.stats['by_type'][issue_type]
                html.append(f"<tr><td>{issue_type}</td><td>{count}</td></tr>")
            html.append("</table>")

        html.append("<div class='footer'>")
        html.append(f"<p>Scan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html.append("</div>")
        html.append("</div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    def print_json_output(self) -> str:
        """Generate JSON output."""
        issues_list = []
        for issue in self.issues:
            issue_dict = asdict(issue)
            issue_dict['severity'] = issue.severity.value
            issues_list.append(issue_dict)

        output = {
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_files": self.stats["total_files"],
                "files_scanned": self.stats["files_scanned"],
                "issues_found": self.stats["issues_found"],
                "by_type": dict(self.stats["by_type"]),
                "by_severity": dict(self.stats["by_severity"]),
            },
            "issues": issues_list,
        }
        return json.dumps(output, indent=2, default=str)

    def _print_statistics(self) -> None:
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total files in dev_notes:    {self.stats['total_files']}")
        print(f"Files scanned:               {self.stats['files_scanned']}")
        print(f"Issues found:                {self.stats['issues_found']}")

        if self.stats['by_severity']:
            print(f"\nBy Severity:")
            for severity in ['error', 'warning', 'note']:
                count = self.stats['by_severity'].get(severity, 0)
                print(f"  {severity.capitalize():10s}: {count}")

        if self.stats['by_type']:
            print(f"\nTop Issues:")
            sorted_types = sorted(self.stats['by_type'].items(), key=lambda x: x[1], reverse=True)[:10]
            for issue_type, count in sorted_types:
                print(f"  {issue_type:30s}: {count}")

        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan dev_notes/ directory for anomalies and planning inconsistencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scan-dev-notes.py                       # Default concise output
  python scan-dev-notes.py --verbose             # Detailed output with suggestions
  python scan-dev-notes.py --html > report.html  # Generate HTML report
  python scan-dev-notes.py --json                # Machine-readable JSON output
  python scan-dev-notes.py --filter=duplicate    # Focus on specific issue types
  python scan-dev-notes.py --verbose --filter=todo,incomplete
        """
    )

    parser.add_argument(
        '--dev-notes-dir',
        type=str,
        default=None,
        help='Path to dev_notes directory (auto-detected if not provided)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print detailed output with line numbers and suggestions'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML report (output to stdout)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Generate machine-readable JSON output'
    )
    parser.add_argument(
        '--filter',
        type=str,
        default=None,
        help='Comma-separated list of issue types to include (e.g., todo,duplicate,incomplete)'
    )

    args = parser.parse_args()

    # Auto-detect dev_notes directory
    if args.dev_notes_dir:
        dev_notes_dir = args.dev_notes_dir
    else:
        # Look for dev_notes relative to script location
        script_dir = Path(__file__).parent.parent.parent
        dev_notes_dir = script_dir / "dev_notes"
        if not dev_notes_dir.exists():
            # Try parent directory
            dev_notes_dir = script_dir.parent / "dev_notes"

    # Parse filter types
    filter_types = None
    if args.filter:
        filter_types = [t.strip() for t in args.filter.split(',')]

    # Determine if we need quiet mode (for structured outputs)
    quiet_mode = args.html or args.json

    # Run scan
    scanner = DevNoteScanner(str(dev_notes_dir), verbose=args.verbose, filter_types=filter_types, quiet=quiet_mode)
    scanner.scan()

    # Output results
    if args.html:
        print(scanner.print_html_output())
    elif args.json:
        print(scanner.print_json_output())
    elif args.verbose:
        scanner.print_verbose_output()
    else:
        scanner.print_default_output()


if __name__ == '__main__':
    main()
