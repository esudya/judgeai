"""Private worker entry point: no config/env secrets, text extraction or diagnostics."""

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

# -I discards cwd/PYTHONPATH; only the trusted application root is added.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.domain.uploads import PdfLimits, UploadRejected, reject_pdf  # noqa: E402


def apply_resource_limits(limits: PdfLimits) -> None:
    if sys.platform != "linux":
        raise reject_pdf("pdf_unavailable")
    import resource

    for key, maximum in (
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_AS, limits.max_memory_bytes),
        (resource.RLIMIT_CPU, limits.max_cpu_seconds),
        (resource.RLIMIT_FSIZE, 4096),
        (resource.RLIMIT_NOFILE, 32),
    ):
        _, hard = resource.getrlimit(key)
        ceiling = maximum if hard == resource.RLIM_INFINITY else min(maximum, hard)
        resource.setrlimit(key, (ceiling, ceiling))


def main():
    logging.disable(logging.CRITICAL)
    try:
        limits = PdfLimits(**json.loads(sys.argv[1]))
        try:
            apply_resource_limits(limits)
        except (OSError, ValueError):
            raise reject_pdf("pdf_unavailable") from None
        from src.infrastructure.pdf_inspector import inspect_pdf

        result = {"ok": True, **asdict(inspect_pdf(sys.stdin.buffer, limits))}
    except UploadRejected as exc:
        result = {"ok": False, "code": exc.code}
    except (MemoryError, RecursionError):
        result = {"ok": False, "code": "pdf_limit"}
    except Exception:
        result = {"ok": False, "code": "pdf_unavailable"}
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
