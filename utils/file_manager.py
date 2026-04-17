"""
Async file management utilities for transcript operations.
Handles path sanitization, directory creation, and safe file I/O.
"""

import re
import shutil
from pathlib import Path
from typing import Optional, List
import aiofiles
import aiofiles.os as aio_os

from config import config


class FileManager:
    """Manages async file operations for transcripts."""

    def __init__(self):
        self.base_dir = config.transcript_dir
        self._ensure_dir_exists_sync()

    def _ensure_dir_exists_sync(self) -> None:
        """Synchronously create transcript directory if missing."""
        self.base_dir.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Remove or replace unsafe characters for cross-platform filenames.
        Replaces: / \ : * ? " < > | with underscores.
        """
        unsafe_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(unsafe_chars, '_', filename)
        # Trim length to 255 characters (common filesystem limit)
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = name[:255 - len(ext) - 1] + ('.' + ext if ext else '')
        return sanitized

    async def write_html(self, content: str, filename: str) -> Path:
        """
        Write HTML content to a file in the transcript directory.
        Returns the full Path to the written file.
        """
        safe_name = self.sanitize_filename(filename)
        file_path = self.base_dir / safe_name
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return file_path

    async def read_html(self, filename: str) -> Optional[str]:
        """Read HTML content from a file. Returns None if file not found."""
        safe_name = self.sanitize_filename(filename)
        file_path = self.base_dir / safe_name
        if not await aio_os.path.exists(file_path):
            return None
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def delete_transcript(self, filename: str) -> bool:
        """Delete a transcript file. Returns True if deleted, False if not found."""
        safe_name = self.sanitize_filename(filename)
        file_path = self.base_dir / safe_name
        try:
            await aio_os.remove(file_path)
            return True
        except FileNotFoundError:
            return False

    async def cleanup_old_transcripts(self, days: int = 30) -> List[Path]:
        """
        Delete transcripts older than `days` from the transcript directory.
        Returns list of deleted file paths.
        """
        deleted = []
        now = await self._get_timestamp()
        async for file_path in self._async_iter_dir():
            if file_path.suffix == '.html':
                stat = await aio_os.stat(file_path)
                mtime = stat.st_mtime
                if (now - mtime) > (days * 86400):
                    await aio_os.remove(file_path)
                    deleted.append(file_path)
        return deleted

    async def _get_timestamp(self) -> float:
        """Return current timestamp (async version)."""
        import time
        return time.time()

    async def _async_iter_dir(self):
        """Async generator yielding Path objects in base_dir."""
        for entry in self.base_dir.iterdir():
            yield entry


# Singleton instance for global import
file_manager = FileManager()