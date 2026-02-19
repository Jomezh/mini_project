import os
import time
import threading
from datetime import datetime


class CleanupManager:
    """
    Manages automatic cleanup of temporary files on the Pi.
    
    Primary deletion: images deleted after CNN result confirms
                      cloud receipt (handled in app_controller.py)
    
    This class handles:
    - Hourly sweep for any leftover files (crashed tests, failed deletes)
    - Size-based cleanup if a folder grows too large
    - Log rotation
    """
    
    CLEANUP_DIRS = {
        'captures': {
            'max_age_hours': 24,      # Images older than 24h are abandoned
            'max_size_mb': 200,       # Hard cap on captures folder
            'extensions': ['.jpg', '.jpeg', '.png']
        },
        'data': {
            'max_age_hours': 48,      # CSVs kept 2 days
            'max_size_mb': 50,
            'extensions': ['.csv']
        },
        'logs': {
            'max_age_hours': 168,     # Logs kept 7 days
            'max_size_mb': 20,
            'extensions': ['.log', '.txt']
        }
    }
    
    # How often to run the cleanup sweep (seconds)
    SWEEP_INTERVAL = 3600  # Every 1 hour
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self._thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start background cleanup thread"""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="CleanupManager"
        )
        self._thread.start()
        print("[CLEANUP] Started - sweeping every hour")
    
    def stop(self):
        """Stop background cleanup"""
        self._stop_event.set()
        print("[CLEANUP] Stopped")
    
    def _loop(self):
        """Run cleanup immediately, then every SWEEP_INTERVAL seconds"""
        self.run_cleanup()
        while not self._stop_event.wait(timeout=self.SWEEP_INTERVAL):
            self.run_cleanup()
    
    def run_cleanup(self):
        """Sweep all configured directories"""
        print(f"[CLEANUP] Sweep at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_deleted = 0
        total_freed_mb = 0.0
        
        for dir_name, cfg in self.CLEANUP_DIRS.items():
            dir_path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(dir_path):
                continue
            
            deleted, freed_mb = self._clean_directory(
                dir_path,
                cfg['max_age_hours'],
                cfg['max_size_mb'],
                cfg['extensions']
            )
            total_deleted += deleted
            total_freed_mb += freed_mb
        
        if total_deleted > 0:
            print(
                f"[CLEANUP] Done: deleted {total_deleted} files, "
                f"freed {total_freed_mb:.2f} MB"
            )
        else:
            print("[CLEANUP] Done: nothing to clean")
    
    def _clean_directory(self, dir_path, max_age_hours, max_size_mb, extensions):
        """
        Clean a directory by:
        1. Removing files older than max_age_hours
        2. Removing oldest files if folder exceeds max_size_mb
        """
        deleted_count = 0
        freed_bytes = 0
        now = time.time()
        max_age_secs = max_age_hours * 3600
        
        # Collect all matching files
        files = []
        for fname in os.listdir(dir_path):
            if not any(fname.lower().endswith(ext) for ext in extensions):
                continue
            fpath = os.path.join(dir_path, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                stat = os.stat(fpath)
                files.append({
                    'path': fpath,
                    'name': fname,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'age_secs': now - stat.st_mtime
                })
            except OSError:
                continue
        
        # Pass 1: Delete by age
        remaining = []
        for f in files:
            if f['age_secs'] > max_age_secs:
                if self._delete_file(f['path'], f['name'], reason="expired"):
                    freed_bytes += f['size']
                    deleted_count += 1
            else:
                remaining.append(f)
        
        # Pass 2: Delete by size (oldest first)
        total_mb = sum(f['size'] for f in remaining) / (1024 * 1024)
        if total_mb > max_size_mb:
            remaining.sort(key=lambda x: x['mtime'])  # Oldest first
            for f in remaining:
                if total_mb <= max_size_mb:
                    break
                if self._delete_file(f['path'], f['name'], reason="size limit"):
                    freed_bytes += f['size']
                    total_mb -= f['size'] / (1024 * 1024)
                    deleted_count += 1
        
        return deleted_count, freed_bytes / (1024 * 1024)
    
    def _delete_file(self, path, name, reason=""):
        """Delete a single file safely"""
        try:
            os.remove(path)
            print(f"[CLEANUP] Deleted ({reason}): {name}")
            return True
        except OSError as e:
            print(f"[CLEANUP] Failed to delete {name}: {e}")
            return False
    
    def get_storage_stats(self):
        """
        Returns current storage usage per directory.
        Useful for a debug screen or logging.
        
        Returns:
            dict: {
                'captures': {'files': 2, 'size_mb': 3.4},
                'data':     {'files': 5, 'size_mb': 0.1},
                'logs':     {'files': 3, 'size_mb': 0.05}
            }
        """
        stats = {}
        for dir_name in self.CLEANUP_DIRS:
            dir_path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(dir_path):
                stats[dir_name] = {'files': 0, 'size_mb': 0.0}
                continue
            
            total_size = 0
            count = 0
            for fname in os.listdir(dir_path):
                fpath = os.path.join(dir_path, fname)
                if os.path.isfile(fpath):
                    total_size += os.path.getsize(fpath)
                    count += 1
            
            stats[dir_name] = {
                'files': count,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }
        return stats
