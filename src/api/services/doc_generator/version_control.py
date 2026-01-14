"""
Document Version Control - Simple file-based version control for documents.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)


class DocumentVersionControl:
    """Simple file-based version control for documents."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.versions_dir = repo_path / '.versions'
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    def commit_file(self, file_path: Path, message: str) -> Optional[str]:
        """Save a version of the file and return version hash."""
        try:
            # Create version hash from timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            version_hash = f"v{timestamp}"
            
            # Create version directory structure
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Save version file
            version_file = version_dir / f"{file_path.stem}_{version_hash}{file_path.suffix}"
            content = file_path.read_text(encoding='utf-8')
            version_file.write_text(content, encoding='utf-8')
            
            # Save metadata
            meta_file = version_dir / f"{file_path.stem}_{version_hash}.meta"
            meta = {
                'hash': version_hash,
                'date': datetime.now().isoformat(),
                'message': message,
                'filename': file_path.name
            }
            meta_file.write_text(json.dumps(meta), encoding='utf-8')
            
            logger.info("File version saved", file=str(rel_path), hash=version_hash)
            return version_hash
        except Exception as e:
            logger.warning("Could not save file version", error=str(e))
            return None
    
    def get_file_history(self, file_path: Path, limit: int = 20) -> List[Dict[str, Any]]:
        """Get version history for a file."""
        try:
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            
            if not version_dir.exists():
                return []
            
            # Find all meta files for this document
            history = []
            pattern = f"{file_path.stem}_v*.meta"
            for meta_file in sorted(version_dir.glob(pattern), reverse=True)[:limit]:
                try:
                    meta = json.loads(meta_file.read_text())
                    history.append({
                        'commit': meta.get('hash', 'unknown'),
                        'date': meta.get('date', ''),
                        'message': meta.get('message', '')
                    })
                except:
                    continue
            
            return history
        except Exception as e:
            logger.warning("Could not get file history", error=str(e))
            return []
    
    def get_file_at_commit(self, file_path: Path, commit: str) -> Optional[str]:
        """Get file content at specific version."""
        try:
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            version_file = version_dir / f"{file_path.stem}_{commit}{file_path.suffix}"
            
            if version_file.exists():
                return version_file.read_text(encoding='utf-8')
            return None
        except Exception as e:
            logger.warning("Could not get file at version", error=str(e))
            return None
