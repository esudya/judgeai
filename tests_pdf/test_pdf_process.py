import contextlib
import io
import json
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from src.domain.uploads import PdfLimits, UploadRejected
from src.infrastructure.pdf_process import PdfProcessInspector
from tests_pdf.fixtures import pdf

ROOT = Path(__file__).resolve().parents[1]


class PdfProcessTests(unittest.TestCase):
    def inspect(self, *, limits=None):
        with tempfile.TemporaryFile() as source:
            source.write(pdf())
            source.seek(0)
            return PdfProcessInspector().inspect(source, limits or PdfLimits())

    @contextlib.contextmanager
    def worker(self, text):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "worker.py"
            script.write_text(text)
            with patch("src.infrastructure.pdf_process._WORKER", script):
                yield

    def test_real_worker_accepts_linux_and_refuses_unprotected_platforms(self):
        if sys.platform == "linux":
            self.assertEqual(self.inspect().pages, 1)
        else:
            with self.assertRaises(UploadRejected) as error:
                self.inspect()
            self.assertEqual(error.exception.code, "pdf_unavailable")

    def test_hung_worker_is_killed_and_reaped_within_parent_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "pid"
            script = (
                "import os,time\n"
                f"open({str(pid_file)!r},'w').write(str(os.getpid()))\n"
                "time.sleep(30)\n"
            )
            start = time.monotonic()
            with self.worker(script), self.assertRaises(UploadRejected) as error:
                self.inspect(limits=replace(PdfLimits(), max_wall_seconds=1))
            self.assertEqual(error.exception.code, "pdf_limit")
            self.assertLess(time.monotonic() - start, 5)
            with self.assertRaises(ProcessLookupError):
                os.kill(int(pid_file.read_text()), 0)

    def test_protocol_invalid_crash_and_oversized_output_fail_closed(self):
        replies = [
            "print('not json')",
            "print('[]')",
            "print('x'*5000)",
            "raise RuntimeError('synthetic-private-marker')",
            'print(\'{"ok":false,"code":[]}\')',
            'print(\'{"ok":true,"pages":true,"objects":2,"decoded_bytes":4}\')',
            'print(\'{"ok":true,"pages":0,"objects":2,"decoded_bytes":4}\')',
            'print(\'{"ok":true,"pages":201,"objects":2,"decoded_bytes":4}\')',
            'print(\'{"ok":true,"pages":1,"objects":2,"decoded_bytes":4,"text":"private"}\')',
        ]
        for script in replies:
            with self.subTest(script=script[:20]), self.worker(script):
                with self.assertRaises(UploadRejected) as error:
                    self.inspect()
                self.assertEqual(error.exception.code, "pdf_unavailable")
                self.assertNotIn("private", str(error.exception))

    def test_unavailable_spawn_is_not_a_format_error_and_capacity_is_released(self):
        with patch(
            "src.infrastructure.pdf_process.subprocess.Popen", side_effect=OSError("private")
        ):
            for _ in range(3):
                with self.assertRaises(UploadRejected) as error:
                    self.inspect()
                self.assertEqual(error.exception.code, "pdf_unavailable")

    def test_busy_worker_capacity_fails_immediately(self):
        with patch("src.infrastructure.pdf_process._CAPACITY", threading.BoundedSemaphore(0)):
            with self.assertRaises(UploadRejected) as error:
                self.inspect()
            self.assertEqual(error.exception.code, "pdf_busy")

    def test_worker_success_and_fixed_rejections_use_bounded_protocol(self):
        with self.worker('print(\'{"ok":true,"pages":1,"objects":2,"decoded_bytes":4}\')'):
            result = self.inspect()
            self.assertEqual((result.pages, result.objects, result.decoded_bytes), (1, 2, 4))
        with self.worker('print(\'{"ok":false,"code":"pdf_encrypted"}\')'):
            with self.assertRaises(UploadRejected) as error:
                self.inspect()
            self.assertEqual(error.exception.code, "pdf_encrypted")

    @unittest.skipUnless(
        sys.platform == "linux", "Hard resource budgets are a Linux deployment contract"
    )
    def test_real_cpu_budget_terminates_a_worker(self):
        script = (
            "import sys\n"
            f"sys.path.insert(0,{str(ROOT)!r})\n"
            "from src.infrastructure.pdf_worker import apply_resource_limits\n"
            "from src.domain.uploads import PdfLimits\n"
            "apply_resource_limits(PdfLimits(max_cpu_seconds=1))\n"
            "while True: pass\n"
        )
        start = time.monotonic()
        with self.worker(script), self.assertRaises(UploadRejected) as error:
            self.inspect(limits=replace(PdfLimits(), max_wall_seconds=4))
        self.assertEqual(error.exception.code, "pdf_limit")
        self.assertLess(time.monotonic() - start, 3)

    @unittest.skipUnless(
        sys.platform == "linux", "Hard resource budgets are a Linux deployment contract"
    )
    def test_real_memory_budget_refuses_allocation(self):
        script = (
            "import sys,json\n"
            f"sys.path.insert(0,{str(ROOT)!r})\n"
            "from src.infrastructure.pdf_worker import apply_resource_limits\n"
            "from src.domain.uploads import PdfLimits\n"
            "apply_resource_limits(PdfLimits(max_memory_bytes=64*1024*1024))\n"
            "try:\n data=bytearray(256*1024*1024)\n"
            "except MemoryError:\n print(json.dumps({'ok':False,'code':'pdf_limit'}))\n"
            "else:\n print(json.dumps({'ok':True,'pages':1,'objects':1,'decoded_bytes':0}))\n"
        )
        with self.worker(script), self.assertRaises(UploadRejected) as error:
            self.inspect()
        self.assertEqual(error.exception.code, "pdf_limit")

    def test_worker_main_never_returns_library_diagnostics_or_document_content(self):
        from src.infrastructure import pdf_worker

        for raw, expected in [(b"private marker", "pdf_invalid"), (pdf(), None)]:
            with self.subTest(raw=raw[:8]):
                output = io.StringIO()
                with (
                    patch.object(pdf_worker, "apply_resource_limits"),
                    patch.object(sys, "argv", ["worker", json.dumps(asdict(PdfLimits()))]),
                    patch.object(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(raw)})()),
                    contextlib.redirect_stdout(output),
                ):
                    previous = logging.root.manager.disable
                    try:
                        pdf_worker.main()
                    finally:
                        logging.disable(previous)
                reply = json.loads(output.getvalue())
                if expected:
                    self.assertEqual(reply, {"ok": False, "code": expected})
                else:
                    self.assertEqual(reply["pages"], 1)
                self.assertNotIn("private", output.getvalue())

    def test_parent_does_not_pass_provider_secrets_into_worker_environment(self):
        script = (
            "import os,json\n"
            "code='pdf_invalid' if 'LLM_API_KEY' not in os.environ else 'pdf_limit'\n"
            "print(json.dumps({'ok':False,'code':code}))"
        )
        with patch.dict(os.environ, {"LLM_API_KEY": "synthetic-only"}), self.worker(script):
            with self.assertRaises(UploadRejected) as error:
                self.inspect()
        self.assertEqual(error.exception.code, "pdf_invalid")
