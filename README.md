# HubICG Agents Catalog

Public, versioned Community catalog of reusable HubICG agent and skill definitions.

This repository contains **definitions and catalog-governance assets only**. It does not contain
the HubICG runtime, adapters, deployment code, private prompt history, customer configuration, or
tenant-specific or proprietary implementation and product features.

## Current catalog

- Five public agent definitions imported from `HUBTECH-DEV/hubicg-community`.
- No public skills have been approved yet; `catalog/skills/` is intentionally empty apart from its
  scope document.
- Every published definition is listed in `catalog/manifest.json` with immutable source and content
  hashes.

## Layout

```text
catalog/
  agents/       Public agent definitions
  skills/       Public skill definitions when approved
  manifest.json Provenance and classification ledger
schemas/        Public data contracts
tools/          Catalog-only validation; never a HubICG runtime
docs/           Publication boundary and governance decisions
```

## Publication rule

Publication is default-deny. A definition reaches this repository only through a pull request,
with explicit `community` classification, provenance, licensing review, secret/privacy checks and
human approval by a HubTech code owner. The source author may propose publication but cannot
approve their own promotion.

See [the publication boundary](docs/PUBLICATION_BOUNDARY.md) and
[the contribution policy](CONTRIBUTING.md).

## Validate locally

```bash
python tools/validate_catalog.py
```

The validator uses only the Python standard library. It verifies the manifest, hashes, schemas'
required contract fields, forbidden private identifiers and repository boundary.

## License

The catalog is offered under `AGPL-3.0-only`; see [LICENSE](LICENSE) and
[LICENSING.md](LICENSING.md). Initial definitions retain their documented provenance from the
public HubICG Community repository. HubTech and HubICG names and marks are not licensed by the
AGPL.
