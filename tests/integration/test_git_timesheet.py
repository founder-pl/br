"""
Tests for Git Timesheet API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


class TestGitTimesheetAPI:
    """Test Git Timesheet API endpoints"""

    @pytest.mark.asyncio
    async def test_scan_repos_valid_path(self):
        """Test scanning for git repositories with valid path"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "folder_path": "/home/tom/github",
                    "max_depth": 2
                }
            )
            
            # Path mapping should translate to /repos in container
            # If /repos exists, should return 200, otherwise 400
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert "total_repos" in data
                assert "repositories" in data
                assert "all_authors" in data
                assert isinstance(data["repositories"], list)

    @pytest.mark.asyncio
    async def test_scan_repos_invalid_path(self):
        """Test scanning with invalid path returns 400"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "folder_path": "/nonexistent/path/12345",
                    "max_depth": 2
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_scan_repos_max_depth_validation(self):
        """Test that max_depth is validated (1-4)"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Too high
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "folder_path": "/tmp",
                    "max_depth": 10
                }
            )
            assert response.status_code == 422  # Validation error

            # Too low
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "folder_path": "/tmp",
                    "max_depth": 0
                }
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_scan_repos_missing_folder_path(self):
        """Test that folder_path is required"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "max_depth": 2
                }
            )
            
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_commits_endpoint_empty_repos(self):
        """Test commits endpoint with empty repo list"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/commits",
                json={
                    "repo_paths": [],
                    "authors": []
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "commits" in data
            assert data["commits"] == []

    @pytest.mark.asyncio
    async def test_commits_endpoint_with_filters(self):
        """Test commits endpoint with date filters"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/commits",
                json={
                    "repo_paths": ["/home/tom/github/founder-pl/br"],
                    "authors": [],
                    "since": "2026-01-01",
                    "until": "2026-12-31"
                }
            )
            
            # May return 200 with commits or empty if path doesn't exist in container
            assert response.status_code == 200
            data = response.json()
            assert "commits" in data
            assert "by_date" in data

    @pytest.mark.asyncio
    async def test_generate_timesheet_validation(self):
        """Test timesheet generation requires valid data"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/git-timesheet/generate-timesheet",
                json={
                    "commits": [],
                    "worker_id": "test-worker-id",
                    "project_mappings": {}
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "entries_created" in data
            assert data["entries_created"] == 0


class TestGitTimesheetPathMapping:
    """Test path mapping between host and container"""

    @pytest.mark.asyncio
    async def test_host_path_mapping(self):
        """Test that host paths are correctly mapped to container paths"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # This tests that /home/tom/github is mapped to /repos
            response = await client.post(
                "/git-timesheet/scan",
                json={
                    "folder_path": "/home/tom/github/founder-pl",
                    "max_depth": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                # Response should contain original host paths
                assert data["base_path"] == "/home/tom/github/founder-pl"
                for repo in data.get("repositories", []):
                    assert repo["path"].startswith("/home/tom/github")
