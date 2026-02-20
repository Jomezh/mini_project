import os
import time
import threading
from datetime import datetime


class CleanupManager:
    """
    Background cleanup of temporary Pi files.
    Primary deletion happens in app_controller after cloud confirmation.
    This handles edge cases: crashes, failed deletes, log rotation.
    """

    CLEANUP_DIRS = {
        'captures': {
            'max_age_hours': 24,
            'max_size_mb':   200,
            'extensions':    ['.jpg', '.jpeg', '.png']
        },
        'data': {
            'max_age_hours': 48,
            'max_size_mb':   50,
            'extensions':    ['.csv']
        },
        'logs': {
            'max_age_hours': 168,    # 7 days
            'max_size_mb':   20,
            'extensions':    ['.log', '.txt']
        }
    }

    SWEEP_INTERVAL = 3600  # Every 1 hour

    def __init__(self, base_dir):
        self.base_dir    = base_dir
        self._thread     = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="CleanupManager"
        )
        self._thread.start()
        print("[CLEANUP] Started - sweeping every hour")

    def stop(self):
        self._stop_event.set()
        print("[CLEANUP] Stopped")

    def _loop(self):
        self.run_cleanup()
        while not self._stop_event.wait(timeout=self.SWEEP_INTERVAL):
            self.run_cleanup()

    def run_cleanup(self):
        print(f"[CLEANUP] Sweep at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        total_deleted = 0
        total_freed   = 0.0

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
            total_freed   += freed_mb

        if total_deleted > 0:
            print(f"[CLEANUP] Done: {total_deleted} files deleted, "
                  f"{total_freed:.2f} MB freed")
        else:
            print("[CLEANUP] Done: nothing to clean")

    def _clean_directory(self, dir_path, max_age_hours, max_size_mb, extensions):
        deleted_count = 0
        freed_bytes   = 0
        now           = time.time()
        max_age_secs  = max_age_hours * 3600

        files = []
        for fname in os.listdir(dir_path):
            if not any(fname.lower().endswith(e) for e in extensions):
                continue
            fpath = os.path.join(dir_path, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                stat = os.stat(fpath)
                files.append({
                    'path':     fpath,
                    'name':     fname,
                    'size':     stat.st_size,
                    'mtime':    stat.st_mtime,
                    'age_secs': now - stat.st_mtime
                })
            except OSError:
                continue

        # Pass 1: age-based deletion
        remaining = []
        for f in files:
            if f['age_secs'] > max_age_secs:
                if self._remove(f['path'], f['name'], "expired"):
                    freed_bytes   += f['size']
                    deleted_count += 1
            else:
                remaining.append(f)

        # Pass 2: size-based deletion (oldest first)
        total_mb = sum(f['size'] for f in remaining) / (1024 * 1024)
        if total_mb > max_size_mb:
            remaining.sort(key=lambda x: x['mtime'])
            for f in remaining:
                if total_mb <= max_size_mb:
                    break
                if self._remove(f['path'], f['name'], "size limit"):
                    freed_bytes   += f['size']
                    total_mb      -= f['size'] / (1024 * 1024)
                    deleted_count += 1

        return deleted_count, freed_bytes / (1024 * 1024)

    def _remove(self, path, name, reason=""):
        try:
            os.remove(path)
            print(f"[CLEANUP] Deleted ({reason}): {name}")
            return True
        except OSError as e:
            print(f"[CLEANUP] Failed to delete {name}: {e}")
            return False

    def get_storage_stats(self):
        stats = {}
        for dir_name in self.CLEANUP_DIRS:
            dir_path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(dir_path):
                stats[dir_name] = {'files': 0, 'size_mb': 0.0}
                continue
            total, count = 0, 0
            for fname in os.listdir(dir_path):
                fpath = os.path.join(dir_path, fname)
                if os.path.isfile(fpath):
                    total += os.path.getsize(fpath)
                    count += 1
            stats[dir_name] = {
                'files':   count,
                'size_mb': round(total / (1024 * 1024), 2)
            }
        return stats
