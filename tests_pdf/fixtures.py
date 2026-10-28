"""Small synthetic PDF packages; no case files or additional runtime dependencies."""

import zlib


def stream(data, *, compressed=False, attrs=b""):
    raw = zlib.compress(data) if compressed else data
    filters = b" /Filter /FlateDecode" if compressed else b""
    return (
        b"<< /Length "
        + str(len(raw)).encode()
        + filters
        + b" "
        + attrs
        + b">>\nstream\n"
        + raw
        + b"\nendstream"
    )


def package(objects):
    result = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)


def pdf(
    *,
    pages=1,
    content=b"BT /F1 12 Tf 72 720 Td (Synthetic judgment.) Tj ET",
    compressed=False,
    extra=(),
    box=b"[0 0 612 792]",
):
    kids = b" ".join(f"{3 + i * 2} 0 R".encode() for i in range(pages))
    font = 3 + pages * 2
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(pages).encode() + b" >>",
    ]
    for index in range(pages):
        objects.extend(
            [
                b"<< /Type /Page /Parent 2 0 R /MediaBox "
                + box
                + f" /Contents {4 + index * 2} 0 R /Resources << ".encode()
                + f"/Font << /F1 {font} 0 R >> >> >>".encode(),
                stream(content, compressed=compressed),
            ]
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return package(objects + list(extra))


def image_pdf():
    return package(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /XObject << /Im1 5 0 R >> >> >>",
            stream(b"q 1 0 0 1 0 0 cm /Im1 Do Q"),
            stream(
                b"\x00",
                attrs=b"/Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/ColorSpace /DeviceGray /BitsPerComponent 8",
            ),
        ]
    )


ENCRYPTED_EMPTY = (
    "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgPDU0MmY2MzkwNzA+Cj4+CmVuZG9iagoy"
    "IDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovQ291bnQgMQovS2lkcyBbIDQgMCBSIF0KPj4KZW5kb2JqCjMg"
    "MCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9U"
    "eXBlIC9QYWdlCi9SZXNvdXJjZXMgPDwKPj4KL01lZGlhQm94IFsgMC4wIDAuMCA2MTIgNzkyIF0KL1Bh"
    "cmVudCAyIDAgUgo+PgplbmRvYmoKNSAwIG9iago8PAovViAyCi9SIDMKL0xlbmd0aCAxMjgKL1AgNDI5"
    "NDk2NzI5MgovRmlsdGVyIC9TdGFuZGFyZAovTyA8MzU2YmU1OTQ0OTgwYjZlMTUwZDk2ZGZiZWFmNjQ5"
    "ZjRiMWUyOTUyNzA0ODkxYzI4MWE1MWEwNzY3NTkxMTU4NT4KL1UgPGJmMzM2NDQxZWU3OTVhYTBhZTVl"
    "OTUzOTRlNWQ0Y2Y2MjhiZjRlNWU0ZTc1OGE0MTY0MDA0ZTU2ZmZmYTAxMDg+Cj4+CmVuZG9iagp4cmVm"
    "CjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA1OSAwMDAw"
    "MCBuIAowMDAwMDAwMTE4IDAwMDAwIG4gCjAwMDAwMDAxNjcgMDAwMDAgbiAKMDAwMDAwMDI2MSAwMDAw"
    "MCBuIAp0cmFpbGVyCjw8Ci9TaXplIDYKL1Jvb3QgMyAwIFIKL0luZm8gMSAwIFIKL0lEIFsgPDM1NjEz"
    "MTMyNjIzNzY0MzczODM1NjEzNjY0MzUzNTM3MzUzNjM5NjI2MjM3MzA2NDMyMzQzMjMyNjEzNzMwMzk+"
    "IDwzNTYxMzEzMjYyMzc2NDM3MzgzNTYxMzY2NDM1MzUzNzM1MzYzOTYyNjIzNzMwNjQzMjM0MzIzMjYx"
    "MzczMDM5PiBdCi9FbmNyeXB0IDUgMCBSCj4+CnN0YXJ0eHJlZgo0NzYKJSVFT0YK"
)


ENCRYPTED_LOCKED = (
    "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgPGIyZDI0ODRjMTU+Cj4+CmVuZG9iagoy"
    "IDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovQ291bnQgMQovS2lkcyBbIDQgMCBSIF0KPj4KZW5kb2JqCjMg"
    "MCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9U"
    "eXBlIC9QYWdlCi9SZXNvdXJjZXMgPDwKPj4KL01lZGlhQm94IFsgMC4wIDAuMCA2MTIgNzkyIF0KL1Bh"
    "cmVudCAyIDAgUgo+PgplbmRvYmoKNSAwIG9iago8PAovViAyCi9SIDMKL0xlbmd0aCAxMjgKL1AgNDI5"
    "NDk2NzI5MgovRmlsdGVyIC9TdGFuZGFyZAovTyA8NmVhZGM1YmU2ZjkwNDhjOTU3ZjQ0NWM0NmQ3ODNk"
    "OGVmYWUxZmFmZmI4OTgwYTE3N2IwMzQ3ZmQ5YjgzMThmZj4KL1UgPDVhMGQ4YjdkODgyNGI0NTA2MWE3"
    "YmU5OWExNDVhMjhmMjhiZjRlNWU0ZTc1OGE0MTY0MDA0ZTU2ZmZmYTAxMDg+Cj4+CmVuZG9iagp4cmVm"
    "CjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA1OSAwMDAw"
    "MCBuIAowMDAwMDAwMTE4IDAwMDAwIG4gCjAwMDAwMDAxNjcgMDAwMDAgbiAKMDAwMDAwMDI2MSAwMDAw"
    "MCBuIAp0cmFpbGVyCjw8Ci9TaXplIDYKL1Jvb3QgMyAwIFIKL0luZm8gMSAwIFIKL0lEIFsgPDM1NjEz"
    "MTMyNjIzNzY0MzczODM1NjEzNjY0MzUzNTM3MzUzNjM5NjI2MjM3MzA2NDMyMzQzMjMyNjEzNzMwMzk+"
    "IDwzNTYxMzEzMjYyMzc2NDM3MzgzNTYxMzY2NDM1MzUzNzM1MzYzOTYyNjIzNzMwNjQzMjM0MzIzMjYx"
    "MzczMDM5PiBdCi9FbmNyeXB0IDUgMCBSCj4+CnN0YXJ0eHJlZgo0NzYKJSVFT0YK"
)


def xref_stream_pdf():
    import re

    original = pdf()
    prefix = original[: original.index(b"xref\n")]
    offsets = [match.start() for match in re.finditer(rb"(?m)^\d+ 0 obj\n", prefix)]
    offsets.append(len(prefix))
    rows = b"\x00" + bytes(4) + b"\xff\xff"
    rows += b"".join(b"\x01" + offset.to_bytes(4, "big") + bytes(2) for offset in offsets)
    result = (
        prefix
        + b"6 0 obj\n"
        + stream(rows, compressed=True, attrs=b"/Type /XRef /Size 7 /W [1 4 2] /Root 1 0 R")
        + b"\nendobj\n"
    )
    return result + f"startxref\n{len(prefix)}\n%%EOF\n".encode()
