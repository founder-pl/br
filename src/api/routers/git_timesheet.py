"""
Git Timesheet Router - Generate timesheets from git repository history

Scans directories for git repositories, extracts commit history,
and generates detailed work schedules based on commit timestamps.
"""

import os
import subprocess
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db

logger = structlog.get_logger()
router = APIRouter()


class GitRepoInfo(BaseModel):
    path: str
    name: str
    authors: List[str]
    commit_count: int
    last_commit: Optional[str]


class GitAuthor(BaseModel):
    name: str
    email: str
    commit_count: int


class GitCommit(BaseModel):
    hash: str
    author_name: str
    author_email: str
    date: datetime
    message: str
    files_changed: int = 0


class ScanRequest(BaseModel):
    folder_path: str = Field(..., description="Base folder to scan for git repos")
    max_depth: int = Field(default=3, ge=1, le=4, description="Max depth to search (1-4)")


class CommitHistoryRequest(BaseModel):
    repo_paths: List[str]
    authors: List[str] = []  # Filter by authors (empty = all)
    since: Optional[str] = None  # Date string YYYY-MM-DD
    until: Optional[str] = None


class GitTimesheetEntry(BaseModel):
    repo_path: str
    repo_name: str
    commit_hash: str
    author: str
    commit_date: datetime
    message: str
    project_id: Optional[str] = None  # B+R project mapping


class GenerateTimesheetRequest(BaseModel):
    commits: List[Dict[str, Any]]
    worker_id: Optional[str] = None
    project_mappings: Dict[str, str] = {}  # repo_path -> project_id


def run_git_command(repo_path: str, args: List[str]) -> str:
    """Run a git command in the specified repository."""
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        logger.error("Git command failed", repo=repo_path, args=args, error=str(e))
        return ""


def is_git_repo(path: str) -> bool:
    """Check if path is a git repository."""
    git_dir = os.path.join(path, '.git')
    return os.path.isdir(git_dir)


def find_git_repos(base_path: str, max_depth: int, current_depth: int = 0) -> List[str]:
    """Recursively find git repositories up to max_depth."""
    repos = []
    
    if current_depth > max_depth:
        return repos
    
    try:
        if is_git_repo(base_path):
            repos.append(base_path)
            return repos  # Don't recurse into git repos
        
        if current_depth < max_depth:
            for entry in os.scandir(base_path):
                if entry.is_dir() and not entry.name.startswith('.'):
                    repos.extend(find_git_repos(entry.path, max_depth, current_depth + 1))
    except PermissionError:
        pass
    except Exception as e:
        logger.warning("Error scanning directory", path=base_path, error=str(e))
    
    return repos


def get_repo_authors(repo_path: str) -> List[GitAuthor]:
    """Get all authors from a git repository with commit counts."""
    output = run_git_command(repo_path, [
        'shortlog', '-sne', '--all'
    ])
    
    authors = []
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
        # Format: "  123\tJohn Doe <john@example.com>"
        match = re.match(r'\s*(\d+)\s+(.+?)\s+<(.+?)>', line)
        if match:
            authors.append(GitAuthor(
                name=match.group(2),
                email=match.group(3),
                commit_count=int(match.group(1))
            ))
    
    return authors


def get_repo_commits(repo_path: str, authors: List[str] = None, 
                     since: str = None, until: str = None) -> List[GitCommit]:
    """Get commit history from a repository."""
    args = [
        'log',
        '--pretty=format:%H|%an|%ae|%aI|%s',
        '--all'
    ]
    
    if since:
        args.append(f'--since={since}')
    if until:
        args.append(f'--until={until}')
    
    output = run_git_command(repo_path, args)
    
    commits = []
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|', 4)
        if len(parts) >= 5:
            author_name = parts[1]
            
            # Filter by authors if specified
            if authors and author_name not in authors:
                continue
            
            try:
                commit_date = datetime.fromisoformat(parts[3].replace('Z', '+00:00'))
            except:
                continue
            
            commits.append(GitCommit(
                hash=parts[0][:8],
                author_name=author_name,
                author_email=parts[2],
                date=commit_date,
                message=parts[4][:200]  # Truncate long messages
            ))
    
    return commits


HOST_TO_CONTAINER_PATH_MAP = {
    "/home/tom/github": "/repos",
}

def translate_path_to_container(host_path: str) -> str:
    """Translate host path to container path."""
    for host_prefix, container_prefix in HOST_TO_CONTAINER_PATH_MAP.items():
        if host_path.startswith(host_prefix):
            return host_path.replace(host_prefix, container_prefix, 1)
    return host_path

def translate_path_to_host(container_path: str) -> str:
    """Translate container path back to host path."""
    for host_prefix, container_prefix in HOST_TO_CONTAINER_PATH_MAP.items():
        if container_path.startswith(container_prefix):
            return container_path.replace(container_prefix, host_prefix, 1)
    return container_path


@router.post("/scan")
async def scan_for_repositories(request: ScanRequest):
    """
    Scan a folder for git repositories up to specified depth.
    Returns list of repositories with their authors.
    """
    base_path = translate_path_to_container(request.folder_path)
    
    if not os.path.isdir(base_path):
        raise HTTPException(status_code=400, detail=f"Folder not found: {request.folder_path} (mapped to {base_path})")
    
    # Find all git repos
    repo_paths = find_git_repos(base_path, request.max_depth)
    
    # Get info for each repo
    repos = []
    all_authors = {}  # Deduplicate authors across repos
    
    for repo_path in repo_paths:
        authors = get_repo_authors(repo_path)
        
        # Get last commit date
        last_commit_output = run_git_command(repo_path, [
            'log', '-1', '--format=%aI'
        ]).strip()
        
        # Count commits
        commit_count_output = run_git_command(repo_path, [
            'rev-list', '--count', '--all'
        ]).strip()
        
        try:
            commit_count = int(commit_count_output)
        except:
            commit_count = 0
        
        host_path = translate_path_to_host(repo_path)
        repos.append(GitRepoInfo(
            path=host_path,
            name=os.path.basename(repo_path),
            authors=[f"{a.name} <{a.email}>" for a in authors],
            commit_count=commit_count,
            last_commit=last_commit_output if last_commit_output else None
        ))
        
        # Collect unique authors
        for author in authors:
            key = f"{author.name}|{author.email}"
            if key not in all_authors:
                all_authors[key] = {
                    "name": author.name,
                    "email": author.email,
                    "commit_count": author.commit_count,
                    "repos": [host_path]
                }
            else:
                all_authors[key]["commit_count"] += author.commit_count
                all_authors[key]["repos"].append(host_path)
    
    return {
        "base_path": request.folder_path,
        "max_depth": request.max_depth,
        "repositories": repos,
        "total_repos": len(repos),
        "all_authors": list(all_authors.values())
    }


@router.post("/commits")
async def get_commit_history(request: CommitHistoryRequest):
    """
    Get commit history from specified repositories.
    Optionally filter by authors and date range.
    """
    all_commits = []
    
    for host_path in request.repo_paths:
        container_path = translate_path_to_container(host_path)
        if not os.path.isdir(container_path):
            continue
        
        commits = get_repo_commits(
            container_path,
            authors=request.authors if request.authors else None,
            since=request.since,
            until=request.until
        )
        
        repo_name = os.path.basename(container_path)
        for commit in commits:
            all_commits.append({
                "repo_path": host_path,
                "repo_name": repo_name,
                "hash": commit.hash,
                "author_name": commit.author_name,
                "author_email": commit.author_email,
                "date": commit.date.isoformat(),
                "hour": commit.date.hour,
                "message": commit.message
            })
    
    # Sort by date
    all_commits.sort(key=lambda x: x["date"], reverse=True)
    
    # Group by date for summary
    by_date = {}
    for commit in all_commits:
        date_str = commit["date"][:10]
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(commit)
    
    return {
        "commits": all_commits,
        "total_commits": len(all_commits),
        "by_date": by_date,
        "date_count": len(by_date)
    }


@router.post("/generate-timesheet")
async def generate_timesheet_from_commits(
    request: GenerateTimesheetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate timesheet entries from git commits.
    Maps commits to time slots and B+R projects.
    """
    entries_created = 0
    entries_by_date = {}
    
    for commit in request.commits:
        commit_date = datetime.fromisoformat(commit["date"].replace('Z', '+00:00'))
        date_str = commit_date.strftime("%Y-%m-%d")
        hour = commit_date.hour
        
        # Map hour to time slot
        if 8 <= hour < 12:
            time_slot = "morning"
        elif 12 <= hour < 16:
            time_slot = "afternoon"
        elif 16 <= hour < 20:
            time_slot = "evening"
        else:
            time_slot = "night"
        
        # Get project mapping
        repo_path = commit.get("repo_path", "")
        project_id = request.project_mappings.get(repo_path)
        
        if not project_id:
            continue
        
        # Track entries
        key = f"{project_id}_{date_str}_{time_slot}"
        if key not in entries_by_date:
            entries_by_date[key] = {
                "project_id": project_id,
                "worker_id": request.worker_id,
                "work_date": date_str,
                "time_slot": time_slot,
                "hours": 4,
                "commits": [],
                "description": ""
            }
        
        entries_by_date[key]["commits"].append({
            "hash": commit["hash"],
            "message": commit["message"][:100],
            "repo": commit.get("repo_name", "")
        })
    
    # Save entries to database
    for key, entry in entries_by_date.items():
        # Build description from commits
        commit_descriptions = [
            f"[{c['repo']}] {c['hash']}: {c['message']}"
            for c in entry["commits"][:5]  # Max 5 commits per entry
        ]
        if len(entry["commits"]) > 5:
            commit_descriptions.append(f"... i {len(entry['commits']) - 5} więcej")
        
        description = "\n".join(commit_descriptions)
        
        try:
            # Convert work_date string to date object for asyncpg
            work_date_obj = date.fromisoformat(entry["work_date"])
            
            await db.execute(
                text("""
                    INSERT INTO read_models.timesheet_entries 
                    (project_id, worker_id, work_date, time_slot, hours, description)
                    VALUES (:project_id, :worker_id, :work_date, :time_slot, :hours, :description)
                    ON CONFLICT (project_id, worker_id, work_date, time_slot)
                    DO UPDATE SET hours = :hours, description = :description, updated_at = NOW()
                """),
                {
                    "project_id": entry["project_id"],
                    "worker_id": entry["worker_id"],
                    "work_date": work_date_obj,
                    "time_slot": entry["time_slot"],
                    "hours": entry["hours"],
                    "description": description
                }
            )
            entries_created += 1
        except Exception as e:
            logger.error("Failed to save timesheet entry", entry=entry, error=str(e))
    
    await db.commit()
    
    return {
        "status": "success",
        "entries_created": entries_created,
        "total_slots": len(entries_by_date),
        "entries": list(entries_by_date.values())
    }


@router.get("/detailed-commits")
async def get_detailed_commits(
    repo_path: str = Query(...),
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None
):
    """Get detailed commit log for a single repository."""
    if not os.path.isdir(repo_path):
        raise HTTPException(status_code=400, detail="Repository not found")
    
    args = [
        'log',
        '--pretty=format:%H|%an|%ae|%aI|%s',
        '--stat',
        '-100'  # Limit to 100 commits
    ]
    
    if author:
        args.append(f'--author={author}')
    if since:
        args.append(f'--since={since}')
    if until:
        args.append(f'--until={until}')
    
    output = run_git_command(repo_path, args)
    
    commits = []
    current_commit = None
    
    for line in output.split('\n'):
        if '|' in line and len(line.split('|')) >= 5:
            # New commit line
            if current_commit:
                commits.append(current_commit)
            
            parts = line.split('|', 4)
            try:
                commit_date = datetime.fromisoformat(parts[3].replace('Z', '+00:00'))
            except:
                continue
            
            current_commit = {
                "hash": parts[0][:8],
                "full_hash": parts[0],
                "author_name": parts[1],
                "author_email": parts[2],
                "date": commit_date.isoformat(),
                "hour": commit_date.hour,
                "message": parts[4],
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0
            }
        elif current_commit and 'files changed' in line:
            # Stats line
            match = re.search(r'(\d+) files? changed', line)
            if match:
                current_commit["files_changed"] = int(match.group(1))
            match = re.search(r'(\d+) insertions?', line)
            if match:
                current_commit["insertions"] = int(match.group(1))
            match = re.search(r'(\d+) deletions?', line)
            if match:
                current_commit["deletions"] = int(match.group(1))
    
    if current_commit:
        commits.append(current_commit)
    
    return {
        "repo_path": repo_path,
        "repo_name": os.path.basename(repo_path),
        "commits": commits,
        "total": len(commits)
    }
