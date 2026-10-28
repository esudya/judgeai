"""Parent deadline, bounded worker output and per-process PDF admission capacity."""

import json
import signal
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path
from typing import BinaryIO

from src.domain.uploads import PdfInspection, PdfLimits, reject_pdf
from src.infrastructure.pdf_inspector import check_pdf_frame

_WORKER = Path(__file__).with_name("pdf_worker.py")
_CAPACITY = threading.BoundedSemaphore(2)


class PdfProcessInspector:
    def inspect(self, source: BinaryIO, limits: PdfLimits) -> PdfInspection:
        check_pdf_frame(source, limits)
        if not _CAPACITY.acquire(blocking=False):
            raise reject_pdf("pdf_busy")
        try:
            with tempfile.TemporaryFile() as output:
                try:
                    process = subprocess.Popen(
                        [sys.executable, "-I", str(_WORKER), json.dumps(asdict(limits))],
                        stdin=source,
                        stdout=output,
                        stderr=subprocess.DEVNULL,
                        env={"LANG": "C.UTF-8"},
                        start_new_session=True,
                    )
                except (OSError, ValueError):
                    raise reject_pdf("pdf_unavailable") from None
                try:
                    process.wait(timeout=limits.max_wall_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise reject_pdf("pdf_limit") from None
                if process.returncode in {-signal.SIGKILL, -signal.SIGXCPU, -signal.SIGXFSZ}:
                    raise reject_pdf("pdf_limit")
                if process.returncode != 0:
                    raise reject_pdf("pdf_unavailable")
                output.seek(0)
                raw = output.read(4097)
                if len(raw) > 4096:
                    raise reject_pdf("pdf_unavailable")
                try:
                    reply = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise reject_pdf("pdf_unavailable") from None
                if not isinstance(reply, dict):
                    raise reject_pdf("pdf_unavailable")
                if reply.get("ok") is False:
                    raise reject_pdf(reply.get("code"))
                fields = ("pages", "objects", "decoded_bytes")
                maximums = (limits.max_pages, limits.max_objects, limits.max_total_decoded_bytes)
                if (
                    reply.get("ok") is not True
                    or set(reply) != {"ok", *fields}
                    or any(
                        type(reply.get(key)) is not int or not 0 <= reply[key] <= maximum
                        for key, maximum in zip(fields, maximums, strict=True)
                    )
                    or reply["pages"] == 0
                    or reply["objects"] == 0
                ):
                    raise reject_pdf("pdf_unavailable")
                return PdfInspection(**{key: reply[key] for key in fields})
        finally:
            _CAPACITY.release()
