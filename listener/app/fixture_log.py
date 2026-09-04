from pathlib import Path


PENDING_LOG_LIMIT = 100


class FixtureRunLog:

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._n = 0
        self._fh = self.path.open('a', encoding='utf-8')
        self.skipped_files: list[str] = []
        self.failed_files: list[tuple[str, str]] = []
        self.pending_files: list[str] = []

    def record_pending(self, filenames: list[str]) -> None:
        self.pending_files = filenames

    def iteration(self, message: str) -> int:
        self._n += 1
        self._fh.write(f'{self._n:04d} {message}\n')
        self._fh.flush()
        return self._n

    def note(self, message: str) -> None:
        self._fh.write(f'     {message}\n')
        self._fh.flush()

    def record_skipped(self, filename: str) -> None:
        self.skipped_files.append(filename)

    def record_failed(self, filename: str, reason: str) -> None:
        self.failed_files.append((filename, reason))

    def write_summary(self) -> None:
        self.note('--- summary ---')
        self.note(f'skipped ({len(self.skipped_files)}):')
        if self.skipped_files:
            for filename in self.skipped_files:
                self.note(f'  {filename}')
        else:
            self.note('  (none)')

        self.note(f'failed ({len(self.failed_files)}):')
        if self.failed_files:
            for filename, reason in self.failed_files:
                self.note(f'  {filename} ({reason})')
        else:
            self.note('  (none)')

        if self.pending_files:
            self.note(f'pending ({len(self.pending_files)}):')
            for filename in self.pending_files[:PENDING_LOG_LIMIT]:
                self.note(f'  {filename}')
            overflow = len(self.pending_files) - PENDING_LOG_LIMIT
            if overflow > 0:
                self.note(f'  ... and {overflow} more')

    def close(self, summary: str = '') -> None:
        self.write_summary()
        if summary:
            self.note(summary)
        self.note(f'finished ({self._n} iterations)')
        self._fh.close()
