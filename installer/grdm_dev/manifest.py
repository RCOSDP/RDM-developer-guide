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
pinned upstream image, `base_image[@base_image_digest]`. A component with `prebuilt_image`
(SPEC-01 §3: a registry reference pinned by digest, allowed only with a `note` and until M4) is
not built at all: `grdm-dev build` records it as `prebuilt`, and `compose render` runs that
reference. The ember-osf-web Dockerfile's schema-1 base image (refused by current Docker) is the
case that made this fallback necessary. The build SHA is the integration
commit when the manifest carries one (`integration_sha`, optional, written by the weekly
integration PR), else the first merged upstream in SPEC-01 rule 3 order (public, then private).
The clone URL is composed at run time from the bare repository name; it is never stored here.

Overlays (SPEC-01 §3 `overlay_of`, ADR-06): a component whose manifest entry names a base component
(`wiki-frontend` → `osf.io`) cannot be built from its own checkout: its Dockerfile COPYs paths of the
base tree (real install run 4 on Mac Studio). Its image is built from a merged context (base checkout
+ overlay files) with the overlay's Dockerfile and is a *bundle builder*, not a runtime: the
wiki-frontend Dockerfile skips the Python steps and only runs `yarn run webpack-prod`. It is tagged
with both commits, `grdm-dev/<overlay id>:<base_sha12>-<overlay_sha12>` (`overlay_tag`), and its
services are one-shot (`templates/<service>.json` has `one_shot: true`, e.g. `wiki_assets`, which
copies the webpack output into the named volume `wiki_static` and exits). The base component keeps
its own image and tag. `Service.origin` is `overlay` for the overlay's services.
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
    prebuilt_image: str | None = None
    overlay_of: str | None = None
    image_build: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    # dict compatibility for modules written against the raw JSON
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    @property
    def is_prebuilt(self) -> bool:
        """True when `prebuilt_image` replaces the build from the integration repository (SPEC-01 §3)."""
        return bool(self.prebuilt_image)

    @property
    def is_image_build(self) -> bool:
        """True for an infra component whose image is built from a Dockerfile inside this repository
        (`image_build: {context, tag}`, SPEC-01 §3, ADR-07): EOL middleware that only ships amd64 images is
        built natively for the host instead of emulated."""
        return self.image_build is not None

    @property
    def is_overlay(self) -> bool:
        """True when `overlay_of` names a base component: this checkout is copied over a copy of the
        base checkout and the image is built from that merged context with this component's Dockerfile
        (SPEC-01 §3, ADR-06). Its services are one-shot bundle copiers."""
        return bool(self.overlay_of)

    @property
    def is_built(self) -> bool:
        """Built locally from the integration repository (never true for a prebuilt component)."""
        return bool(self.integration_repo) and not self.is_prebuilt

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
        if self.is_prebuilt:
            return str(self.prebuilt_image)
        if self.is_image_build:
            return f"{LOCAL_IMAGE_PREFIX}/{self.id.lower()}:{self.image_build['tag']}"
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

    def overlay_for(self, base_id: str) -> Component | None:
        """The overlay component applied on top of `base_id`, or None (SPEC-01 §3 `overlay_of`)."""
        for c in self.components:
            if c.overlay_of == base_id:
                return c
        return None

    @property
    def service_names(self) -> list[str]:
        return [s for c in self.components for s in c.services]


def overlay_tag(base_sha12: str | None, overlay_sha12: str | None) -> str:
    """Image tag of an overlay component: `<base_sha12>-<overlay_sha12>` (SPEC-01 §3), both commits
    the image was built from. Either half falls back to `develop` when the manifest pins no SHA."""
    return f"{base_sha12 or 'develop'}-{overlay_sha12 or 'develop'}"


@dataclass(frozen=True)
class BuildInfo:
    repo: str          # integration repository name, e.g. RDM-osf.io-dev2027 (name only, SPEC-01 rule 5)
    branch: str        # always develop
    sha: str | None    # 40-hex commit the image is built from, when the manifest knows it
    sha12: str | None  # the image tag: the sha12, or `<base_sha12>-<overlay_sha12>` for an overlay component
    overlay_of: str | None = None   # base component id whose checkout is the build context (SPEC-01 §3)
    base_repo: str | None = None    # the base's integration repository name
    base_sha12: str | None = None   # the base's pinned sha12


@dataclass
class Service:
    name: str
    component: str
    role: str
    image: str
    profile: str
    build: BuildInfo | None
    template: dict[str, Any] = field(default_factory=dict, repr=False)
    prebuilt_image: str | None = None  # set when the component bypasses the build (SPEC-01 §3)
    image_build: bool = False  # built from a Dockerfile in this repository (SPEC-01 §3 image_build, ADR-07)

    @property
    def is_built(self) -> bool:
        return self.build is not None

    @property
    def is_prebuilt(self) -> bool:
        return bool(self.prebuilt_image)

    @property
    def is_overlay_build(self) -> bool:
        """The image is built from the base checkout with this component's files copied over it (SPEC-01 §3)."""
        return self.build is not None and bool(self.build.overlay_of)

    @property
    def is_one_shot(self) -> bool:
        """The container runs to completion and exits (template `one_shot: true`, Compose `restart: "no"`)."""
        return bool(self.template.get("one_shot"))

    @property
    def origin(self) -> str:
        """`built` (from the integration repository), `overlay` (merged base + overlay context, bundle
        builder), `prebuilt` (registry image by digest), `image` (infra built from a Dockerfile in this
        repository, ADR-07) or `pinned` (infra from a registry)."""
        if self.is_prebuilt:
            return "prebuilt"
        if self.is_overlay_build:
            return "overlay"
        if self.image_build:
            return "image"
        return "built" if self.is_built else "pinned"


# --------------------------------------------------------------------------- loading


def _path_of(ctx_or_path: Any) -> Path:
    if isinstance(ctx_or_path, (str, Path)):
        return Path(ctx_or_path)
    return Path(ctx_or_path.manifest_path)


def _root_of(ctx_or_path: Any) -> Path:
    if isinstance(ctx_or_path, (str, Path)):
        return Path(ctx_or_path).resolve().parent.parent
    return Path(ctx_or_path.root)


def _image_build_of(c: dict[str, Any]) -> dict[str, Any] | None:
    """`image_build` as a validated dict, None when the key is absent. An empty object or a missing key is a
    ManifestError: it must never silently turn the component into a plain pinned image (PR #34 review r1 R1-02)."""
    if "image_build" not in c:
        return None
    ib = c["image_build"]
    if not isinstance(ib, dict) or not isinstance(ib.get("context"), str) or not ib["context"] or not isinstance(ib.get("tag"), str) or not ib["tag"]:
        raise ManifestError([f"MC-15: component {c.get('id')!r}: image_build must be an object with non-empty string context and tag (got {ib!r})"])
    return dict(ib)


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
                    prebuilt_image=c.get("prebuilt_image") or None,
                    overlay_of=c.get("overlay_of") or None,
                    image_build=_image_build_of(c),
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
    image tag actually built (from the build report: the sha12, or `<base>-<overlay>` for a base
    component with an overlay) and overrides the manifest-derived tag.

    An overlay component (`overlay_of`) yields its own services, which must be one-shot (template
    `one_shot: true`; MC-14 otherwise); their image is `grdm-dev/<overlay>:<base_sha12>-<overlay_sha12>`
    and their origin is `overlay`. The base component's services are unaffected.
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
        base = manifest.component(comp.overlay_of) if comp.is_overlay else None
        for name in comp.services:
            tpl = templates.get(name)
            if base is not None and not (tpl or {}).get("one_shot"):
                raise ManifestError([f"MC-14: service {name!r} of overlay {comp.id} must be one-shot (template one_shot: true); an overlay image is a bundle builder, not a runtime"])
            if PROFILE_RANK[service_profile(comp, tpl)] > rank:
                continue
            if name in SHIBBOLETH_SERVICES and not use_shib:
                continue
            if name == "fakecas" and use_shib:
                continue
            build = None
            if comp.is_built:  # false for a prebuilt component: no BuildInfo, build-report tags do not apply
                manifest_tag = overlay_tag(base.sha12, comp.sha12) if base else comp.sha12
                sha12 = (image_tags or {}).get(comp.id) or manifest_tag
                build = BuildInfo(
                    repo=comp.integration_repo or "", branch=comp.integration_branch or "develop", sha=comp.build_sha, sha12=sha12,
                    overlay_of=base.id if base else None,
                    base_repo=base.integration_repo if base else None,
                    base_sha12=base.sha12 if base else None,
                )
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
                    prebuilt_image=comp.prebuilt_image,
                    image_build=comp.is_image_build,
                )
            )
    return out


def service_names(services: Iterable[Service]) -> list[str]:
    return [s.name for s in services]
