#!/usr/bin/env python3
"""Validate the repository's management contract using only the standard library.

This checks metadata and required files, not product behavior or GitHub settings.
It never runs manifest commands, follows external links, or modifies files.
"""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATES = ["backlog", "ready", "in_progress", "blocked", "in_review", "done"]
DOCUMENT_KEYS = {"instructions", "brief", "architecture", "status", "decisions", "handoffs"}
REQUIRED_FILES = [
    "README.md", "AGENTS.md", "CONTRIBUTING.md", ".gitignore",
    ".agents/skills/rayggxia-project-collab/SKILL.md",
    ".agents/skills/rayggxia-project-collab/agents/openai.yaml",
    ".github/CODEOWNERS", ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/task.yml", ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/ISSUE_TEMPLATE/config.yml", ".github/workflows/project-structure.yml",
    "docs/decisions/_template.md", "docs/handoffs/_template.md", "config/labels.json",
    "config/status-mapping.json", "docs/COLLABORATION.md", "progress/README.md", "work/README.md",
]


def main():
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def check_file(relative):
        if not isinstance(relative, str) or not relative.strip():
            errors.append("Document paths must be nonempty strings.")
            return
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            errors.append("Path must stay inside this repository: " + relative)
            return
        if Path(relative).is_absolute() or "\\" in relative or ":" in relative:
            errors.append("Use a repository-relative POSIX path: " + relative)
        elif not path.is_file():
            errors.append("Missing required file: " + relative)
        else:
            try:
                if not path.read_text(encoding="utf-8-sig").strip():
                    errors.append("Required file is empty: " + relative)
            except (OSError, UnicodeError) as exc:
                errors.append("Cannot read required UTF-8 file " + relative + ": " + str(exc))

    try:
        manifest = json.loads((ROOT / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print("FAIL: Cannot read project.json: " + str(exc))
        return 1
    if not isinstance(manifest, dict):
        print("FAIL: project.json must contain an object.")
        return 1

    require(type(manifest.get("schema_version")) is int and manifest.get("schema_version") == 1,
            "schema_version must be the integer 1.")
    project_id = manifest.get("project_id")
    require(isinstance(project_id, str) and bool(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", project_id)),
            "project_id must be a stable lowercase kebab-case identifier.")
    require(isinstance(manifest.get("name"), str) and bool(manifest.get("name", "").strip()),
            "name must be a nonempty string.")
    lifecycle = manifest.get("lifecycle")
    require(lifecycle in ("template", "planned", "active", "paused", "completed", "archived"),
            "lifecycle must be template, planned, active, paused, completed, or archived.")

    sections = {}
    for key in ("owner", "repository", "workflow", "sources_of_truth", "documents", "checks"):
        value = manifest.get(key)
        require(isinstance(value, dict), key + " must be an object.")
        sections[key] = value if isinstance(value, dict) else {}

    owner = sections["owner"].get("github_handle")
    repository = sections["repository"]
    full_name = repository.get("full_name")
    branch = repository.get("default_branch")
    if lifecycle != "template":
        require(project_id != "project-template", "Replace the template project_id before activation.")
        require(isinstance(owner, str) and bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner)),
                "Set owner.github_handle to a real responsible account.")
        require(isinstance(full_name, str) and bool(re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", full_name)),
                "Set repository.full_name to owner/repository.")
        require(isinstance(branch, str) and bool(branch.strip()),
                "Set repository.default_branch to the actual default branch.")
    require(repository.get("intended_visibility") in ("private", "internal", "public"),
            "repository.intended_visibility must be private, internal, or public.")
    workflow = sections["workflow"]
    require(workflow.get("task_source_of_truth") == "github_issues", "Tasks must use github_issues as their source of truth.")
    require(workflow.get("states") == STATES, "workflow.states must match the shared six-state workflow.")
    require(workflow.get("branch_pattern") == "task/<issue-number>-<short-slug>", "Keep the documented task branch pattern.")
    require(workflow.get("review_delivery") == "pull_request", "review_delivery must be pull_request.")

    expected_sources = {
        "tasks_and_assignees": "github_issues",
        "portfolio_view": "github_projects_if_configured",
        "access_control": "github_repository_and_organization_settings",
        "context_and_decisions": "repository_documents",
    }
    require(sections["sources_of_truth"] == expected_sources, "sources_of_truth must keep the shared responsibility mapping.")
    documents = sections["documents"]
    require(set(documents) == DOCUMENT_KEYS, "documents must define instructions, brief, architecture, status, decisions, and handoffs.")
    for relative in list(documents.values()) + REQUIRED_FILES:
        check_file(relative)
    require(sections["checks"].get("management_structure") == "python scripts/check_project.py",
            "checks.management_structure must point to this validator.")
    product_tests = sections["checks"].get("product_tests")
    require(product_tests is None or (isinstance(product_tests, str) and bool(product_tests.strip())),
            "checks.product_tests must be null or a documented command string.")
    try:
        label_config = json.loads((ROOT / "config/labels.json").read_text(encoding="utf-8-sig"))
        require(isinstance(label_config, dict) and type(label_config.get("schema_version")) is int
                and label_config.get("schema_version") == 1, "Label configuration must use schema_version 1.")
        labels = label_config.get("labels", []) if isinstance(label_config, dict) else []
        require(isinstance(labels, list) and bool(labels), "labels must be a nonempty list.")
        label_names = []
        for label in labels if isinstance(labels, list) else []:
            if not isinstance(label, dict):
                errors.append("Each label must be an object.")
                continue
            name, color = label.get("name"), label.get("color")
            if isinstance(name, str) and name.strip():
                label_names.append(name)
            else:
                errors.append("Each label must have a nonempty name.")
            require(isinstance(color, str) and bool(re.fullmatch(r"[0-9A-Fa-f]{6}", color)),
                    "Label colors must be six hexadecimal digits.")
        require(len(label_names) == len(set(label_names)), "Label names must be unique.")
        require({"type:task", "type:bug", *("status:" + state for state in STATES)} <= set(label_names),
                "Labels must cover the issue form types and all workflow states.")
    except (OSError, ValueError) as exc:
        errors.append("Cannot read config/labels.json: " + str(exc))
    try:
        mapping_config = json.loads((ROOT / "config/status-mapping.json").read_text(encoding="utf-8-sig"))
        if not isinstance(mapping_config, dict):
            errors.append("Status mapping must contain an object.")
        else:
            require(type(mapping_config.get("schema_version")) is int
                    and mapping_config.get("schema_version") == 1, "Status mapping must use schema_version 1.")
            require(mapping_config.get("task_state_source") == "issue_status_label",
                    "Status mapping must use the Issue status label as its source of truth.")
            require(mapping_config.get("projects_status_field") == "Status",
                    "Status mapping must identify the Projects Status field.")
            display_names = ["Backlog", "Ready", "In progress", "Blocked", "In review", "Done"]
            expected_mappings = [
                {"state": state, "issue_label": "status:" + state, "project_status": display}
                for state, display in zip(STATES, display_names)
            ]
            require(mapping_config.get("mappings") == expected_mappings,
                    "Status mappings must cover the six workflow states with their exact labels and display names.")
    except (OSError, ValueError) as exc:
        errors.append("Cannot read config/status-mapping.json: " + str(exc))
    if errors:
        print("FAIL: Project management structure is invalid:")
        for error in errors:
            print("- " + error)
        return 1
    print("PASS: Project management structure is valid (schema 1).")
    if lifecycle == "template":
        print("NOTE: Template mode; project identity and live GitHub settings are not configured.")
    print("NOTE: This does not validate product behavior, permissions, or live GitHub settings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
