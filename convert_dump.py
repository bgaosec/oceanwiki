#!/usr/bin/env python3
"""Convert a MediaWiki XML dump plus attachments into a Markdown site."""
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


EXPORT_NS = "{http://www.mediawiki.org/xml/export-0.11/}"
PAGE_TAG = f"{EXPORT_NS}page"
TITLE_TAG = f"{EXPORT_NS}title"
NS_TAG = f"{EXPORT_NS}ns"
REVISION_TAG = f"{EXPORT_NS}revision"
TEXT_TAG = f"{EXPORT_NS}text"


def normalize_title(title: str) -> str:
    """Normalize a page title for consistent slugging."""
    return unicodedata.normalize("NFC", title.strip())


_slug_non_alnum_re = re.compile(r"[^0-9A-Za-z\-]+")
_slug_dash_re = re.compile(r"-+")


def slugify(title: str) -> str:
    """Return a filesystem-friendly slug for *title*."""
    normalized = unicodedata.normalize("NFKD", title)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("\u00A0", " ")
    normalized = normalized.lower()
    normalized = normalized.replace(" ", "-")
    normalized = _slug_non_alnum_re.sub("-", normalized)
    normalized = _slug_dash_re.sub("-", normalized)
    normalized = normalized.strip("-")
    return normalized or "page"


class SlugRegistry:
    """Assign unique slugs to page titles."""

    def __init__(self) -> None:
        self._slug_counts: Dict[str, int] = defaultdict(int)
        self._title_to_slug: Dict[str, str] = {}

    def ensure_slug(self, title: str) -> str:
        title = normalize_title(title)
        if not title:
            title = "untitled"
        if title in self._title_to_slug:
            return self._title_to_slug[title]
        base = slugify(title)
        count = self._slug_counts[base]
        slug = base if count == 0 else f"{base}-{count + 1}"
        self._slug_counts[base] = count + 1
        self._title_to_slug[title] = slug
        return slug

    def slug_for(self, title: str) -> Optional[str]:
        title = normalize_title(title)
        return self._title_to_slug.get(title)

    def items(self):
        return self._title_to_slug.items()


ATTACHMENT_OPTION_PREFIXES = (
    "thumb",
    "thumbnail",
    "frame",
    "frameless",
    "border",
    "right",
    "left",
    "center",
    "none",
)


class WikiToMarkdownConverter:
    def __init__(
        self,
        slug_registry: SlugRegistry,
        attachments_root: Path,
        output_root: Path,
        copy_attachments: bool,
    ) -> None:
        self.slug_registry = slug_registry
        self.attachments_root = attachments_root
        self.output_root = output_root
        self.copy_attachments = copy_attachments
        self.attachments_map: Dict[str, List[Path]] = defaultdict(list)
        self.copied_attachments: Set[str] = set()
        self.missing_attachments: Set[str] = set()
        if self.copy_attachments:
            self._build_attachment_index()

    def _build_attachment_index(self) -> None:
        if not self.attachments_root.exists():
            return
        for path in self.attachments_root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            variants = {name, name.replace(" ", "_"), name.replace("_", " ")}
            for variant in variants:
                key = variant.lower()
                if path not in self.attachments_map[key]:
                    self.attachments_map[key].append(path)

    def convert(self, text: str, attachments_used: Set[str]) -> str:
        if not text:
            return ""
        text = html.unescape(text)
        text = self._strip_refs(text)
        text = self._convert_headings(text)
        text = self._convert_formatting(text)
        text = self._convert_external_links(text)
        text = self._convert_internal_links(text, attachments_used)
        text = self._cleanup_templates(text)
        text = self._normalize_whitespace(text)
        return text.strip() + "\n"

    def _strip_refs(self, text: str) -> str:
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<references[^>]*/?>", "", text, flags=re.IGNORECASE)
        return text

    def _convert_headings(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            level = len(match.group(1))
            level = max(1, min(level, 6))
            content = match.group(2).strip()
            return f"{'#' * level} {content}\n"

        return re.sub(r"^(=+)\s*(.*?)\s*\1\s*$", repl, text, flags=re.MULTILINE)

    def _convert_formatting(self, text: str) -> str:
        text = text.replace("'''''", "***")
        text = text.replace("'''", "**")
        text = text.replace("''", "*")
        return text

    def _convert_external_links(self, text: str) -> str:
        def repl_double(match: re.Match[str]) -> str:
            url = match.group(1)
            label = match.group(2)
            return f"[{label.strip()}]({url})"

        text = re.sub(r"\[\[(https?://[^\s\]]+)\s+([^\]]+)\]\]", repl_double, text)

        def repl(match: re.Match[str]) -> str:
            url = match.group(1)
            label = match.group(2)
            if label:
                return f"[{label.strip()}]({url})"
            return f"<{url}>"

        return re.sub(r"\[(https?://[^\s\]]+)(?:\s+([^\]]+))?\]", repl, text)

    def _convert_internal_links(self, text: str, attachments_used: Set[str]) -> str:
        def repl(match: re.Match[str]) -> str:
            inner = match.group(1)
            parts = [part.strip() for part in inner.split("|")]
            target = parts[0] if parts else ""
            display = parts[-1] if len(parts) > 1 else target
            target_lower = target.lower()
            if target_lower.startswith("file:") or target_lower.startswith("image:"):
                filename = target.split(":", 1)[1].strip()
                caption = self._choose_caption(parts[1:]) or filename
                attachments_used.add(filename)
                return f"![{caption}](../attachments/{filename})"
            if ":" in target and not target_lower.startswith("http"):
                # Ignore non-main namespace links by returning display text.
                return display or target
            slug = self.slug_registry.ensure_slug(target)
            label = display or target
            return f"[{label}](./{slug}.md)"

        return re.sub(r"\[\[([^\]]+)\]\]", repl, text)

    def _choose_caption(self, options: Iterable[str]) -> str:
        for option in reversed([opt for opt in options if opt]):
            lower = option.lower()
            if any(lower.startswith(prefix) for prefix in ATTACHMENT_OPTION_PREFIXES):
                continue
            if lower.startswith("alt="):
                return option.split("=", 1)[1]
            if lower.startswith("link=") or lower.startswith("page="):
                continue
            return option
        return ""

    def _cleanup_templates(self, text: str) -> str:
        # Remove common template markers that don't translate well.
        text = re.sub(r"\{\{[^\}]+\}\}", "", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        # Collapse more than two blank lines.
        return re.sub(r"\n{3,}", "\n\n", text)

    def copy_attachment(self, filename: str) -> Optional[Path]:
        if not self.copy_attachments:
            return None
        key_candidates = {
            filename,
            filename.replace(" ", "_"),
            filename.replace("_", " "),
        }
        candidates: List[Path] = []
        for candidate in key_candidates:
            paths = self.attachments_map.get(candidate.lower())
            if paths:
                candidates.extend(paths)
        if not candidates:
            self.missing_attachments.add(filename)
            return None
        source = candidates[0]
        dest_dir = self.output_root / "attachments"
        dest_dir.mkdir(parents=True, exist_ok=True)
        requested_name = Path(filename).name
        dest = dest_dir / requested_name
        if requested_name not in self.copied_attachments:
            shutil.copy2(source, dest)
            self.copied_attachments.add(requested_name)
        return dest


def parse_dump(
    xml_path: Path,
    attachments_root: Path,
    output_root: Path,
    namespaces: Optional[Set[int]] = None,
    *,
    copy_attachments: bool,
) -> None:
    slug_registry = SlugRegistry()
    converter = WikiToMarkdownConverter(
        slug_registry, attachments_root, output_root, copy_attachments
    )

    pages_dir = output_root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    index_entries: List[tuple[str, str]] = []
    referenced_attachments: Set[str] = set()

    context = ET.iterparse(xml_path, events=("end",))
    for _, elem in context:
        if elem.tag != PAGE_TAG:
            continue
        title_elem = elem.find(TITLE_TAG)
        ns_elem = elem.find(NS_TAG)
        title = title_elem.text if title_elem is not None else ""
        namespace = int(ns_elem.text) if ns_elem is not None and ns_elem.text else 0
        if namespaces is not None and namespace not in namespaces:
            elem.clear()
            continue
        revision_elem = elem.find(REVISION_TAG)
        text_elem = revision_elem.find(TEXT_TAG) if revision_elem is not None else None
        text = text_elem.text if text_elem is not None else ""

        slug = slug_registry.ensure_slug(title)
        attachments_used: Set[str] = set()
        markdown_body = converter.convert(text or "", attachments_used)
        page_path = pages_dir / f"{slug}.md"
        with page_path.open("w", encoding="utf-8") as fp:
            fp.write(f"# {title}\n\n")
            fp.write(markdown_body)
        index_entries.append((title, slug))
        for attachment in attachments_used:
            referenced_attachments.add(attachment)
        elem.clear()

    if copy_attachments and referenced_attachments:
        for filename in sorted(referenced_attachments):
            converter.copy_attachment(filename)

    manifest_path = output_root / "attachments-manifest.txt"
    with manifest_path.open("w", encoding="utf-8") as fp:
        if not referenced_attachments:
            fp.write("No attachments were referenced in this export.\n")
        else:
            fp.write(
                "Attachment\tStatus\n"
                "---------\t------\n"
            )
            for filename in sorted(referenced_attachments):
                if filename in converter.copied_attachments:
                    status = "copied"
                elif copy_attachments:
                    if filename in converter.missing_attachments:
                        status = "missing (not found in attachments directory)"
                    else:
                        status = "not copied (copy skipped)"
                else:
                    status = "not copied (run with --copy-attachments to include)"
                fp.write(f"{filename}\t{status}\n")

    index_entries.sort(key=lambda item: item[0].lower())
    index_path = output_root / "index.md"
    with index_path.open("w", encoding="utf-8") as fp:
        fp.write("# OceanAtmosWiki Markdown Export\n\n")
        fp.write("Generated from MediaWiki XML dump.\n\n")
        for title, slug in index_entries:
            fp.write(f"- [{title}](pages/{slug}.md)\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml_dump", type=Path, help="Path to the MediaWiki XML dump file")
    parser.add_argument(
        "--attachments",
        type=Path,
        default=Path("oceanwiki"),
        help="Directory containing MediaWiki attachment files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("site"),
        help="Destination directory for the generated Markdown site",
    )
    parser.add_argument(
        "--namespaces",
        type=int,
        nargs="*",
        default=[0],
        help="Namespace IDs to include (default: main namespace 0)",
    )
    parser.add_argument(
        "--copy-attachments",
        action="store_true",
        help="Copy referenced attachments into the output directory",
    )
    args = parser.parse_args()

    output_root = args.output.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    parse_dump(
        args.xml_dump,
        args.attachments,
        output_root,
        set(args.namespaces),
        copy_attachments=args.copy_attachments,
    )


if __name__ == "__main__":
    main()
