# mcps

The catalog of remote MCP servers that HelloSeal and Axiom Studio agents can connect to.

Servers here are connected, never installed: each entry is a remote endpoint plus how to sign in to it. There are no images, packages or local commands. HelloSeal lists every entry in its connections catalog.

Every entry is curated by the Axiom Studio team and maintained through pull requests.

## Layout

```
servers/
  <slug>/
    mcp.yaml        required
    logo.<ext>      optional: logo.svg, logo.png, logo.jpg, logo.webp or logo.gif
schema/
  mcp.schema.json   JSON Schema for mcp.yaml
scripts/
  validate.py       validates the whole repository
```

The slug is the server directory's path relative to `servers/`, for example `servers/linear/mcp.yaml` has slug `linear` and `servers/neondatabase/mcp-server-neon/mcp.yaml` has slug `neondatabase/mcp-server-neon`.

- Pattern `^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$`, at most one `/`, no `..`, no `//`.
- A server directory may not contain another server directory.
- A server directory holds only `mcp.yaml` and at most one logo. No other files.

## mcp.yaml

Keys are snake_case and no other keys are allowed. Leave out optional keys that are empty or false.

| Key | Required | Type | Rules |
| --- | --- | --- | --- |
| `name` | yes | string | 1–256 bytes |
| `summary` | no | string | up to 2048 bytes; one or two sentences |
| `description` | no | string | up to 65536 bytes, Markdown; leave out when empty or identical to `summary` |
| `category` | no | string | `^[a-z0-9-]{0,64}$` |
| `tags` | no | list of strings | up to 32, unique, each `^[a-z0-9+#. -]{1,64}$` |
| `official` | no | bool | `true` when the vendor maintains the server; default `false` |
| `registry_name` | no | string | name in the official MCP registry, e.g. `io.github.zoom/zoom-workspace` |
| `docs_url` | no | string | http(s) URL |
| `website_url` | no | string | http(s) URL |
| `endpoints` | yes | list | 1–16 items, unique `url` |

Each endpoint:

| Key | Values |
| --- | --- |
| `url` | `https://` URL of the remote MCP endpoint |
| `transport` | `streamable-http` or `sse` |
| `auth` | `oauth`, `api-key`, `none` or `unknown` |

Example:

```yaml
name: Zoom
summary: Search meetings, retrieve recordings and AI summaries from a Zoom account.
description: |-
  Longer Markdown description.

  [Setup documentation](https://example.com/docs)
category: productivity
tags:
  - productivity
  - remote-mcp
official: true
registry_name: io.github.zoom/zoom-workspace
docs_url: https://example.com/docs
endpoints:
  - url: https://mcp.zoom.us/mcp/zoom/streamable
    transport: streamable-http
    auth: oauth
```

Use block-style YAML. Strings are used exactly as written, so prefer `|-` blocks for multi-line text.

## Logos

- At most one of `logo.svg`, `logo.png`, `logo.jpg`, `logo.webp`, `logo.gif`.
- 1 to 262144 bytes.
- The extension must match the content: PNG, JPEG, GIF and WebP are recognized by their file signature; anything else is treated as SVG.
- SVGs are sanitized and checked for monochrome automatically, so there is no field for that. Prefer a square SVG without scripts, external references or embedded fonts.

## Adding, editing or removing a server

Open a pull request.

- Add: create `servers/<slug>/mcp.yaml` (and optionally a logo). Pick the slug carefully: use the vendor or `owner/project` name.
- Edit: change the files in the server's directory.
- Remove: delete the server's directory. This retires the server from the catalog.
- Never rename a slug. Slugs are permanent identities and existing connections reference them. If a server moves, edit its endpoints in place.

CI runs the validator on every push and pull request.

## Validating locally

```sh
pip install pyyaml jsonschema
python3 scripts/validate.py
```

It checks every `mcp.yaml` against the schema, the slug and directory rules, logo count, size and type, unique endpoint URLs and stray files, prints a summary and exits non-zero on any error.
