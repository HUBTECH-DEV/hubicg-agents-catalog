#!/usr/bin/env python3
"""Fail-closed validator for the public definitions-only catalog."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "catalog" / "manifest.json"
AGENT_SCHEMA_PATH = ROOT / "schemas" / "agent-v1.schema.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SOURCE_REPOSITORY = "HUBTECH-DEV/hubicg-community"
SOURCE_COMMIT = "96571dd232d3ce744705c76b5062aa2b4f422d36"
SOURCE_PARENT = PurePosixPath(".hubicg/roles")

FORBIDDEN_TOP_LEVEL = {
    ".promptsConfig",
    ".promptsHistory",
    ".promptsLibrary",
    "adapters",
    "config",
    "connectors",
    "deploy",
    "portal",
    "private",
    "runtime",
    "src",
}
FORBIDDEN_ASSET_TERMS = (
    "begin private key",
    "client_secret",
    "smtp_pass",
)
REQUIRED_AGENT_FIELDS = {"schemaVersion", "id", "name", "instructions"}
REQUIRED_ENTRY_FIELDS = {
    "type",
    "id",
    "path",
    "classification",
    "license",
    "contentSha256",
    "sourceRepository",
    "sourceVisibility",
    "sourcePath",
    "sourceCommitSha",
    "sourceBlobSha",
}


class CatalogError(ValueError):
    pass


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"JSON inválido em {path.relative_to(ROOT)}: {exc}") from exc


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_digest(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def validate_schema_instance(data: object, schema: object, relative: str) -> None:
    """Validate the supported draft-2020-12 subset without external dependencies."""

    if not isinstance(data, dict) or not isinstance(schema, dict):
        raise CatalogError(f"{relative}: definição/schema deve ser objeto JSON")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise CatalogError("schema público sem properties/required válidos")

    missing = [field for field in required if field not in data]
    if missing:
        raise CatalogError(f"{relative}: campos obrigatórios ausentes: {', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        extra = sorted(set(data) - set(properties))
        if extra:
            raise CatalogError(f"{relative}: campos não permitidos: {', '.join(extra)}")

    for field, value in data.items():
        rule = properties.get(field)
        if not isinstance(rule, dict):
            raise CatalogError(f"{relative}: regra ausente para {field}")
        if "const" in rule and value != rule["const"]:
            raise CatalogError(f"{relative}: {field} diverge do valor constante")
        expected_type = rule.get("type")
        if expected_type == "string":
            if not isinstance(value, str):
                raise CatalogError(f"{relative}: {field} deve ser string")
            if len(value) < rule.get("minLength", 0) or len(value) > rule.get("maxLength", sys.maxsize):
                raise CatalogError(f"{relative}: tamanho inválido em {field}")
            if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
                raise CatalogError(f"{relative}: formato inválido em {field}")
        elif expected_type == "array":
            if not isinstance(value, list):
                raise CatalogError(f"{relative}: {field} deve ser array")
            if len(value) > rule.get("maxItems", sys.maxsize):
                raise CatalogError(f"{relative}: itens demais em {field}")
            if rule.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
                raise CatalogError(f"{relative}: itens duplicados em {field}")
            item_rule = rule.get("items", {})
            for item in value:
                if item_rule.get("type") == "string" and not isinstance(item, str):
                    raise CatalogError(f"{relative}: item não textual em {field}")
                if "pattern" in item_rule and re.fullmatch(item_rule["pattern"], item) is None:
                    raise CatalogError(f"{relative}: item inválido em {field}")


def ensure_repository_boundary() -> None:
    present = {child.name for child in ROOT.iterdir()}
    forbidden = sorted(present & FORBIDDEN_TOP_LEVEL)
    if forbidden:
        raise CatalogError(f"diretórios privados/runtime proibidos: {', '.join(forbidden)}")

    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            raise CatalogError(f"symlink proibido: {path.relative_to(ROOT)}")


def validate_asset(entry: dict[str, object]) -> str:
    missing = sorted(REQUIRED_ENTRY_FIELDS - entry.keys())
    if missing:
        raise CatalogError(f"entrada sem campos obrigatórios: {', '.join(missing)}")

    item_type = entry["type"]
    item_id = entry["id"]
    relative = entry["path"]
    if item_type != "agent":
        raise CatalogError("skills permanecem bloqueadas até a aprovação de um schema específico")
    if not isinstance(item_id, str) or not SLUG.fullmatch(item_id):
        raise CatalogError(f"id inválido: {item_id!r}")
    if not isinstance(relative, str):
        raise CatalogError(f"path inválido para {item_id}")

    pure = PurePosixPath(relative)
    expected_parent = PurePosixPath("catalog") / f"{item_type}s"
    if pure.is_absolute() or ".." in pure.parts or pure.parent != expected_parent:
        raise CatalogError(f"path fora do catálogo {item_type}: {relative}")
    if pure.suffix != ".json" or pure.stem != item_id:
        raise CatalogError(f"path e id divergem: {relative} / {item_id}")

    if entry["classification"] != "community":
        raise CatalogError(f"{item_id}: classificação deve ser community")
    if entry["license"] != "AGPL-3.0-only":
        raise CatalogError(f"{item_id}: licença inesperada")
    if entry["sourceVisibility"] != "public":
        raise CatalogError(f"{item_id}: fonte não pública")
    if entry["sourceRepository"] != SOURCE_REPOSITORY:
        raise CatalogError(f"{item_id}: repositório de origem não aprovado")
    if not isinstance(entry["sourceCommitSha"], str) or not HEX40.fullmatch(entry["sourceCommitSha"]):
        raise CatalogError(f"{item_id}: sourceCommitSha inválido")
    if entry["sourceCommitSha"] != SOURCE_COMMIT:
        raise CatalogError(f"{item_id}: sourceCommitSha não aprovado")
    if not isinstance(entry["sourceBlobSha"], str) or not HEX40.fullmatch(entry["sourceBlobSha"]):
        raise CatalogError(f"{item_id}: sourceBlobSha inválido")
    if not isinstance(entry["contentSha256"], str) or not HEX64.fullmatch(entry["contentSha256"]):
        raise CatalogError(f"{item_id}: contentSha256 inválido")

    path = ROOT / Path(*pure.parts)
    if not path.is_file():
        raise CatalogError(f"arquivo ausente: {relative}")
    if digest(path) != entry["contentSha256"]:
        raise CatalogError(f"hash divergente: {relative}")
    if git_blob_digest(path) != entry["sourceBlobSha"]:
        raise CatalogError(f"Git blob divergente: {relative}")

    source_path = entry["sourcePath"]
    if not isinstance(source_path, str):
        raise CatalogError(f"{item_id}: sourcePath inválido")
    source_pure = PurePosixPath(source_path)
    if source_pure.parent != SOURCE_PARENT or source_pure.name != pure.name:
        raise CatalogError(f"{item_id}: sourcePath fora da origem pública aprovada")

    raw = path.read_text(encoding="utf-8")
    lowered = raw.lower()
    forbidden = [term for term in FORBIDDEN_ASSET_TERMS if term in lowered]
    if forbidden or EMAIL.search(raw):
        raise CatalogError(f"{relative}: possível identificador privado, e-mail ou segredo")

    data = load_json(path)
    schema = load_json(AGENT_SCHEMA_PATH)
    validate_schema_instance(data, schema, relative)
    assert isinstance(data, dict)
    if data.get("id") != item_id or data.get("schemaVersion") != "1.0":
        raise CatalogError(f"{relative}: id/schemaVersion divergem do manifesto")
    if item_type == "agent" and not REQUIRED_AGENT_FIELDS <= data.keys():
        raise CatalogError(f"{relative}: campos obrigatórios de agent ausentes")
    for field in ("name", "instructions"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise CatalogError(f"{relative}: {field} deve ser texto não vazio")
    return relative


def main() -> int:
    try:
        ensure_repository_boundary()
        manifest = load_json(MANIFEST_PATH)
        if not isinstance(manifest, dict) or manifest.get("schemaVersion") != "1.0":
            raise CatalogError("manifesto ausente ou schemaVersion inválido")
        if manifest.get("license") != "AGPL-3.0-only":
            raise CatalogError("licença do catálogo deve ser AGPL-3.0-only")
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            raise CatalogError("entries deve ser uma lista")

        paths: set[str] = set()
        ids: set[tuple[object, object]] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise CatalogError("entrada do manifesto deve ser objeto")
            key = (entry.get("type"), entry.get("id"))
            if key in ids:
                raise CatalogError(f"entrada duplicada: {key}")
            ids.add(key)
            relative = validate_asset(entry)
            if relative in paths:
                raise CatalogError(f"path duplicado: {relative}")
            paths.add(relative)

        actual = {
            path.relative_to(ROOT).as_posix()
            for folder in (ROOT / "catalog" / "agents", ROOT / "catalog" / "skills")
            for path in folder.glob("*.json")
        }
        if paths != actual:
            missing = sorted(actual - paths)
            stale = sorted(paths - actual)
            raise CatalogError(f"manifesto divergente; sem entrada={missing}, sem arquivo={stale}")

        for schema in (ROOT / "schemas").glob("*.json"):
            load_json(schema)
    except CatalogError as exc:
        print(f"catalog-policy: FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"catalog-policy: OK: {len(paths)} definição(ões) pública(s) validada(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
