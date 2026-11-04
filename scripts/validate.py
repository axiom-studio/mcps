#!/usr/bin/env python3
"""Validate every server in servers/. Exits non-zero on any error.

Usage: python3 scripts/validate.py [repo-root]
Requires: pyyaml, jsonschema
"""
import json
import os
import re
import sys

import jsonschema
import yaml

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
SERVERS = os.path.join(ROOT, "servers")
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
LOGO_EXTS = ("svg", "png", "jpg", "webp", "gif")
MAX_LOGO = 262144
BYTE_LIMITS = {"name": 256, "summary": 2048, "description": 65536}


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        keys.add(key)
    return loader.construct_mapping(node, deep=deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def logo_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "svg"


def main():
    with open(os.path.join(ROOT, "schema", "mcp.schema.json")) as f:
        validator = jsonschema.Draft202012Validator(json.load(f))
    errors = []
    servers = []
    logos = 0

    def err(where, msg):
        errors.append(f"{where}: {msg}")

    if not os.path.isdir(SERVERS):
        print(f"no servers/ directory in {ROOT}")
        return 1

    for dirpath, dirnames, filenames in os.walk(SERVERS):
        dirnames.sort()
        rel = os.path.relpath(dirpath, SERVERS).replace(os.sep, "/")
        if rel == ".":
            for f in filenames:
                err(f"servers/{f}", "stray file (servers/ holds only server directories)")
            continue
        if "mcp.yaml" in filenames:
            servers.append(rel)
            for d in dirnames:
                err(f"servers/{rel}/{d}", "directory inside a server directory (servers may not be nested)")
            dirnames[:] = []
        elif filenames:
            for f in filenames:
                err(f"servers/{rel}/{f}", "stray file outside a server directory")
        elif not dirnames:
            err(f"servers/{rel}", "empty directory")

    for slug in servers:
        where = f"servers/{slug}"
        if not SLUG_RE.match(slug) or ".." in slug or "//" in slug or slug.count("/") > 1:
            err(where, "invalid slug (pattern ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$, at most one '/', no '..')")
        d = os.path.join(SERVERS, slug)
        files = sorted(os.listdir(d))
        logo_files = [f for f in files if f in tuple(f"logo.{e}" for e in LOGO_EXTS)]
        for f in files:
            if f != "mcp.yaml" and f not in logo_files:
                err(f"{where}/{f}", "stray file (only mcp.yaml and one logo.<svg|png|jpg|webp|gif> allowed)")
        if len(logo_files) > 1:
            err(where, f"more than one logo: {', '.join(logo_files)}")
        for f in logo_files:
            with open(os.path.join(d, f), "rb") as fh:
                data = fh.read()
            if not 1 <= len(data) <= MAX_LOGO:
                err(f"{where}/{f}", f"logo must be 1..{MAX_LOGO} bytes (is {len(data)})")
            kind = logo_type(data)
            if f != f"logo.{kind}":
                err(f"{where}/{f}", f"content is {kind}, rename to logo.{kind}")
            if kind == "svg" and b"<svg" not in data.lower():
                err(f"{where}/{f}", "not a PNG/JPEG/GIF/WebP and no <svg> element found")
        logos += 1 if logo_files else 0

        try:
            with open(os.path.join(d, "mcp.yaml"), "rb") as fh:
                doc = yaml.load(fh.read().decode("utf-8"), Loader=UniqueKeyLoader)
        except (UnicodeDecodeError, yaml.YAMLError) as e:
            err(f"{where}/mcp.yaml", f"cannot parse: {e}")
            continue
        for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            path = "/".join(str(p) for p in e.path) or "(root)"
            err(f"{where}/mcp.yaml", f"{path}: {e.message}")
        if not isinstance(doc, dict):
            continue
        for key, limit in BYTE_LIMITS.items():
            v = doc.get(key)
            if isinstance(v, str) and len(v.encode("utf-8")) > limit:
                err(f"{where}/mcp.yaml", f"{key} exceeds {limit} bytes")
        if doc.get("description") is not None and doc.get("description") in ("", doc.get("summary")):
            err(f"{where}/mcp.yaml", "description is empty or identical to summary; omit it")
        for key in ("summary", "category", "registry_name", "docs_url", "website_url"):
            if doc.get(key) == "":
                err(f"{where}/mcp.yaml", f"{key} is empty; omit it")
        if doc.get("tags") == []:
            err(f"{where}/mcp.yaml", "tags is empty; omit it")
        if doc.get("official") is False:
            err(f"{where}/mcp.yaml", "official: false is the default; omit it")
        eps = doc.get("endpoints")
        if isinstance(eps, list):
            urls = [e.get("url") for e in eps if isinstance(e, dict)]
            dup = sorted({u for u in urls if urls.count(u) > 1})
            if dup:
                err(f"{where}/mcp.yaml", f"duplicate endpoint url: {', '.join(map(str, dup))}")

    lower = {}
    for slug in servers:
        lower.setdefault(slug.lower(), []).append(slug)
    for group in lower.values():
        if len(group) > 1:
            err("servers", f"slugs differ only by case: {', '.join(group)}")

    for e in errors:
        print(f"error: {e}")
    print(f"{len(servers)} servers, {logos} with logos, "
          f"{sum('/' in s for s in servers)} slugs with '/', {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
