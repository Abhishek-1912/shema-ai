"""Build a small, valid, text-based PDF from plain text — no extra library needed.

Used by tests and by scripts.make_sample_files. Each string in `pages` becomes one PDF page.
Only basic ASCII text is supported (other characters become '?').
"""

import textwrap

LINE_WIDTH = 95  # characters per line
LINE_HEIGHT = 14  # points
TOP = 790  # y position of the first line (A4 page is 842 points tall)


def _escape(line: str) -> str:
    line = line.encode("ascii", errors="replace").decode("ascii")
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content_stream(page_text: str) -> bytes:
    lines: list[str] = []
    for paragraph in page_text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, LINE_WIDTH) or [""])
    commands = [f"BT /F1 11 Tf 50 {TOP} Td {LINE_HEIGHT} TL"]
    commands += [f"({_escape(line)}) Tj T*" for line in lines]
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def build_simple_pdf(pages: list[str]) -> bytes:
    if not pages:
        raise ValueError("A PDF needs at least one page.")

    objects: list[bytes] = []  # object number = index + 1

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog = add(b"")  # placeholder, filled once we know the pages object number
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_numbers = []
    for text in pages:
        stream = _content_stream(text)
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (pages_obj, font, content)
        )
        page_numbers.append(page)

    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj
    kids = b" ".join(b"%d 0 R" % n for n in page_numbers)
    objects[pages_obj - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_numbers))

    # Write the file and remember where each object starts (the "xref" table needs byte offsets).
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog,
        xref_start,
    )
    return bytes(out)
