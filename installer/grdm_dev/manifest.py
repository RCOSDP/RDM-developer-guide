"""grdm-dev manifest — load and validate manifest/upstreams.json, derive services (SPEC-01, SPEC-02 §4).

Three jobs:

* `load(ctx_or_path)` parses the manifest into dataclasses (`Manifest`, `Component`, `Upstream`, `PR`).
  Components stay dict-compatible (`comp["id"]`, `comp.get(...)`) so modules written against the
  raw JSON keep working.
* `validate(ctx_or_path)` runs the SPEC-01 §5 checks (MC-01..MC-11, MC-13) by delegating to
  tools/manifest_check.py, which stays the single implementation. An empty list means valid;
  callers map a non-empty list to exit 20 (`exit_codes.MANIFEST_INVALID`).
* `services_for_profile(manifest, profile, auth)` turns components into `Service` objects for one
  profile, following the SPEC-02 §4 table. Service templates under `templates/<service>.json`
  (SPEC-02 §3 `compose render`) supply the service-level profile where it differs from the
  component (`admin` and `worker` belong to `osf.io`, profile minimum, but are core services).

Images: a component with an integration repository is built locally as
`grdm-dev/<component id, lower case>:<sha12>` (same rule as build.py); an infra component runs its
pinned upstream image, `base_image[@base_image_digest]`. The build SHA is the integration
commit when the manifest carries one (`integration_sha`, optional, written by the weekly
integration PR), else the first merged upstream in SPEC-01 rule 3 order (public, then private).
The clone URL is composed at run time from the bare repository name; it is never stored here.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import exit_codes

PROFILES: tuple[str, ...] = ("minimum", "core", "full")
PROFILE_RANK: dict[str, int] = {name: i for i, name in enumerate(PROFILES)}
DEFAULT_PROFILE = "core"
LOCAL_IMAGE_PREFIX = "grdm-dev"
TEMPLATE_DIR = Path(__file__).parent / "templates"

# SPEC-02 §4: the `shibboleth` auth variant swaps fakecas for shibboleth_sp + test_idp in `full`.
AUTH_FAKECAS = "fakecas"
AUTH_SHIBBOLETH = "shibboleth"
SHIBBOLETH_SERVICES: frozenset[str] = frozenset({"shibboleth_sp", "test_idp"})


class ManifestError(Exception):
    """The manifest is invalid (exit 20). `errors` holds one line per finding."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors) if errors else "manifest invalid")
        self.errors = errors
        self.exit_code = exit_codes.MANIFEST_INVALID


@dataclass(frozen=True)
class Upstream:
    repo: str
    branch: str
    kind: str
    tracking_branch: str
    status: str
    sha: str
    fetched_at: str


@dataclass(frozen=True)
class PR:
    repo: str
    number: int
    title: str
    reason: str
    status: str


@dataclass
class Component:
    id: str
    role: str
    services: list[str]
    integration_repo: str | None
    integration_branch: str | None
    upstreams: list[Upstream]
    adopted_prs: list[PR]
    candidate_prs: list[PR]
    base_image: str
    base_image_digest: str | None
    target_image: dict[str, str | None]
    profile: str
    platforms: list[str]
    note: str | None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    # dict compatibility for modules written against the raw JSON
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    @property
    def is_built(self) -> bool:
        return bool(self.integration_repo)

    @property
    def build_sha(self) -> str | None:
        """Commit the local image is built from (see module docstring)."""
        explicit = self.raw.get("integration_sha")
        if isinstance(explicit, str) and explicit:
            return explicit
        for kind in ("public", "private"):
            for up in self.upstreams:
                if up.kind == kind and up.status == "merged":
                    return up.sha
        return None

    @property
    def sha12(self) -> str | None:
        sha = self.build_sha
        return sha[:12] if sha else None

    @property
    def pinned_image(self) -> str:
        """Infra: the upstream image, with its digest once pinned (SPEC-03 §3.4)."""
        if self.base_image_digest:
            return f"{self.base_image}@{self.base_image_digest}"
        return self.base_image

    def local_image(self, sha12: str | None = None) -> str:
        return f"{LOCAL_IMAGE_PREFIX}/{self.id.lower()}:{sha12 or self.sha12 or 'develop'}"

    def image_reference(self, sha12: str | None = None) -> str:
        return self.local_image(sha12) if self.is_built else self.pinned_image


@dataclass
class Manifest:
    schema_version: int
    generated_at: str
    note: str | None
    components: list[Component]
    path: Path | None = None

    def component(self, component_id: str) -> Component:
        for c in self.components:
            if c.id == component_id:
                return c
        raise KeyError(component_id)

    def component_for_service(self, service: str) -> Component:
        for c in self.components:
            if service in c.services:
                return c
        raise KeyError(service)

    @property
    def service_names(self) -> list[str]:
        return [s for c in self.components for s in c.services]


@dataclass(frozen=True)
class BuildInfo:
    repo: str          # integration repository name, e.g. RDM-osf.io-dev2027 (name only, SPEC-01 rule 5)
    branch: str        # always develop
    sha: str | None    # 40-hex commit the image is built from, when the manifest knows it
    sha12: str | None


@dataclass
class Service:
    name: str
    component: str
    role: str
    image: str
    profile: str
    build: BuildInfo | None
    template: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_built(self) -> bool:
        return self.build is not None


# --------------------------------------------------------------------------- loading


def _path_of(ctx_or_path: Any) -> Path:
    if isinstance(ctx_or_path, (str, Path)):
        return Path(ctx_or_path)
    return Path(ctx_or_path.manifest_path)


def _root_of(ctx_or_path: Any) -> Path:
    if isinstance(ctx_or_path, (str, Path)):
        return Path(ctx_or_path).resolve().parent.parent
    return Path(ctx_or_path.root)


def parse(data: dict[str, Any], path: Path | None = None) -> Manifest:
    """Build the dataclasses from already-parsed JSON. Raises ManifestError on a structural problem."""
    try:
        components = []
        for c in data["components"]:
            components.append(
                Component(
                    id=c["id"],
                    role=c["role"],
                    services=list(c["services"]),
                    integration_repo=c.get("integration_repo"),
                    integration_branch=c.get("integration_branch"),
                    upstreams=[Upstream(**{k: u[k] for k in Upstream.__dataclass_fields__}) for u in c.get("upstreams", [])],
                    adopted_prs=[PR(**{k: p[k] for k in PR.__dataclass_fields__}) for p in c.get("adopted_prs", [])],
                    candidate_prs=[PR(**{k: p[k] for k in PR.__dataclass_fields__}) for p in c.get("candidate_prs", [])],
                    base_image=c["base_image"],
                    base_image_digest=c.get("base_image_digest"),
                    target_image=dict(c.get("target_image") or {}),
                    profile=c["profile"],
                    platforms=list(c.get("platforms", [])),
                    note=c.get("note"),
                    raw=c,
                )
            )
        return Manifest(
            schema_version=int(data["schema_version"]),
            generated_at=str(data["generated_at"]),
            note=data.get("note"),
            components=components,
            path=path,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ManifestError([f"MC-01: manifest structure invalid: {exc.__class__.__name__}: {exc}"]) from exc


def load(ctx_or_path: Any) -> Manifest:
    """Parse manifest/upstreams.json. Accepts a Context or a path. Raises ManifestError (exit 20)."""
    path = _path_of(ctx_or_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError([f"MC-01: {path} not found"]) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError([f"MC-01: {path} is not valid JSON: {exc}"]) from exc
    if not isinstance(data, dict):
        raise ManifestError([f"MC-01: {path} must contain a JSON object"])
    return parse(data, path)


# --------------------------------------------------------------------------- validation


def _checker_module(root: Path):
    """Import tools/manifest_check.py (the one SPEC-01 implementation) from the repository root.

    Falls back to the copy next to this package (installer/../tools) so tests that use a temporary
    root still validate with the real checker.
    """
    candidates = [root / "tools" / "manifest_check.py", Path(__file__).resolve().parents[2] / "tools" / "manifest_check.py"]
    for cand in candidates:
        if cand.exists():
            name = "grdm_dev._manifest_check"
            spec = importlib.util.spec_from_file_location(name, cand)
            if spec is None or spec.loader is None:  # pragma: no cover
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("tools/manifest_check.py not found; it is the SPEC-01 checker")


def validate(ctx_or_path: Any) -> list[str]:
    """Run SPEC-01 §5 checks. Returns [] when valid; otherwise one line per finding (exit 20)."""
    json_path = _path_of(ctx_or_path)
    toon_path = json_path.with_suffix(".toon")
    try:
        checker = _checker_module(_root_of(ctx_or_path))
    except FileNotFoundError as exc:
        return [f"MC-01: {exc}"]
    try:
        return list(checker.check_manifest_files(json_path, toon_path))
    except Exception as exc:  # the checker must never end in a traceback (same rule as its main())
        return [f"MC-01: manifest could not be validated: {exc.__class__.__name__}: {exc}"]


def load_validated(ctx_or_path: Any) -> Manifest:
    """validate() then load(); raises ManifestError carrying the findings."""
    errors = validate(ctx_or_path)
    if errors:
        raise ManifestError(errors)
    return load(ctx_or_path)


# --------------------------------------------------------------------------- templates and services


def load_templates(template_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read templates/<service>.json. Keyed by service name; a template's `service` field must match its file."""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((template_dir or TEMPLATE_DIR).glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            tpl = json.load(fh)
        name = tpl.get("service", path.stem)
        if name != path.stem:
            raise ValueError(f"template {path.name}: service field {name!r} does not match the file name")
        out[name] = tpl
    return out


def service_profile(component: Component, template: dict[str, Any] | None) -> str:
    """The smallest profile that includes a service: the template may narrow the component's profile."""
    prof = (template or {}).get("profile") or component.profile
    if prof not in PROFILE_RANK:
        raise ManifestError([f"MC-10: unknown profile {prof!r} for component {component.id}"])
    return prof


def services_for_profile(
    manifest: Manifest,
    profile: str = DEFAULT_PROFILE,
    auth: str = AUTH_FAKECAS,
    templates: dict[str, dict[str, Any]] | None = None,
    image_tags: dict[str, str] | None = None,
) -> list[Service]:
    """Services started by `profile`, in manifest order (SPEC-02 §4).

    `auth` is `fakecas` (default) or `shibboleth`; the latter is only meaningful for `full`, where it
    removes `fakecas` and adds `shibboleth_sp` and `test_idp`. `image_tags` maps component id to the
    sha12 actually built (from the build report) and overrides the manifest-derived tag.
    """
    if profile not in PROFILE_RANK:
        raise ValueError(f"unknown profile {profile!r}; expected one of {', '.join(PROFILES)}")
    if auth not in (AUTH_FAKECAS, AUTH_SHIBBOLETH):
        raise ValueError(f"unknown auth {auth!r}; expected fakecas or shibboleth")
    templates = templates if templates is not None else load_templates()
    rank = PROFILE_RANK[profile]
    use_shib = profile == "full" and auth == AUTH_SHIBBOLETH
    out: list[Service] = []
    for comp in manifest.components:
        for name in comp.services:
            tpl = templates.get(name)
            if PROFILE_RANK[service_profile(comp, tpl)] > rank:
                continue
            if name in SHIBBOLETH_SERVICES and not use_shib:
                continue
            if name == "fakecas" and use_shib:
                continue
            build = None
            if comp.is_built:
                sha12 = (image_tags or {}).get(comp.id) or comp.sha12
                build = BuildInfo(repo=comp.integration_repo or "", branch=comp.integration_branch or "develop", sha=comp.build_sha, sha12=sha12)
            else:
                sha12 = None
            out.append(
                Service(
                    name=name,
                    component=comp.id,
                    role=comp.role,
                    image=comp.image_reference(sha12),
                    profile=service_profile(comp, tpl),
                    build=build,
                    template=tpl or {},
                )
            )
    return out


def service_names(services: Iterable[Service]) -> list[str]:
    return [s.name for s in services]
