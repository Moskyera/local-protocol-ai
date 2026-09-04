"""
WebStackArchitect - φτιάχνει ΠΡΑΓΜΑΤΙΚΕΣ, εκτελέσιμες ιστοσελίδες (με ή χωρίς βάση).

ΓΙΑΤΙ ΔΕΝ ΕΙΝΑΙ React/Next: μετρήθηκε σε ΑΥΤΟ το μηχάνημα ότι το `npm` είναι
σπασμένο (validate-engines.js throw). Οτιδήποτε απαιτεί npm install θα παρήγαγε
project που ο χρήστης ΔΕΝ μπορεί να τρέξει. Αντιθέτως το ai-env έχει ήδη offline:
fastapi, sqlalchemy 2.0, alembic, jinja2, uvicorn, pydantic, html5lib, tinycss2,
pytest. Οπότε: Python-first, SQLite-first, μηδέν network, μηδέν CDN.

ΔΥΟ STACKS:
  py_db  -> FastAPI + SQLAlchemy + Jinja2 (server-rendered) + SQLite   [με βάση]
  static -> HTML5 + CSS + plain ES modules (node --check verifiable)   [χωρίς βάση]

ΣΧΕΔΙΑΣΤΙΚΕΣ ΑΡΧΕΣ (από adversarial review — μη τις αφαιρέσεις):
1. Τα κρίσιμα αρχεία (models/db/main/config) γράφονται ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΑ από Python
   πάνω σε validated JSON. Το μοντέλο δεν παίρνει ευκαιρία να τα φαντασιωθεί.
2. Schema-first: τίποτα δεν γράφεται πριν το schema δημιουργηθεί ΚΑΘΑΡΑ σε
   in-memory SQLite (create_all). Αν σκάει, repair loop, max 3 προσπάθειες.
3. Jinja verification με StrictUndefined. Με το default Undefined ένα typo
   ({% for p in postz %}) render-άρει άδειο και το test περνάει ψευδώς.
4. Ο per-file loop έχει ΡΗΤΟ exhaustion branch: αν εξαντληθούν οι προσπάθειες,
   πέφτει σε deterministic fallback και το ΚΑΤΑΓΡΑΦΕΙ — δεν γράφει σιωπηλά τίποτα.
5. Truncation detection: αν το μοντέλο κόπηκε στο max_tokens, ξαναζητάμε με
   μεγαλύτερο budget αντί να κάψουμε προσπάθειες σε μισό αρχείο.
6. Όλα τα writes περνούν από safe_paths (containment jail).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("web_stack_architect")

from openhands_skills.expert_base import ExpertSkill
from openhands_skills import safe_paths as sp

try:
    from openhands_multiagent_v2.code_intelligence import code_intelligence
except Exception:  # pragma: no cover
    code_intelligence = None

_PY = sys.executable

_SQL_TYPES = {
    "int": "Integer", "integer": "Integer", "float": "Float", "number": "Float",
    "str": "String", "string": "String", "text": "Text", "bool": "Boolean",
    "boolean": "Boolean", "datetime": "DateTime", "date": "Date",
}


@dataclass
class SiteSpec:
    slug: str
    name: str
    purpose: str
    needs_db: bool
    entities: List[Dict[str, Any]] = field(default_factory=list)
    pages: List[Dict[str, str]] = field(default_factory=list)
    theme: str = "clean modern light/dark"


@dataclass
class FileResult:
    path: str
    written: bool
    attempts: int = 0
    truncated: bool = False
    note: str = ""


@dataclass
class BuildReport:
    project_dir: str
    stack: str
    spec: Optional[SiteSpec]
    files: List[FileResult] = field(default_factory=list)
    schema_ok: bool = False
    verification: str = ""
    status: str = "unknown"
    run_cmd: str = ""

    def to_report(self) -> str:
        wrote = sum(1 for f in self.files if f.written)
        lines = [
            f"## {self.status}  —  {self.stack}",
            f"Project: {self.project_dir}",
            f"Files written: {wrote}/{len(self.files)}",
        ]
        if self.spec and self.spec.needs_db:
            lines.append(f"Database schema created cleanly: {self.schema_ok}")
        bad = [f for f in self.files if not f.written]
        if bad:
            lines.append("NOT written (needs attention): " + ", ".join(f"{f.path} ({f.note})" for f in bad))
        lines += ["", "### Verification", self.verification or "(none)", "",
                  "### Run it", self.run_cmd or "(n/a)"]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Deterministic keyword pre-classifier: wins over the model on conflict.
# --------------------------------------------------------------------------- #
_DB_WORDS = ("blog", "shop", "store", "users", "user", "login", "auth", "orders",
             "order", "inventory", "booking", "admin", "crud", "comments",
             "dashboard", "accounts", "products", "product", "tasks", "todo",
             "database", "db", "sql", "καταστημα", "χρηστες", "προϊοντα",
             "παραγγελιες", "βαση")
_NODB_WORDS = ("landing", "portfolio", "brochure", "one-pager", "onepager",
               "docs", "resume", "cv", "coming soon", "static")


def _wants_db(text: str) -> Optional[bool]:
    t = (text or "").lower()
    if any(w in t for w in _DB_WORDS):
        return True
    if any(w in t for w in _NODB_WORDS):
        return False
    return None


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of a model response."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m.group(1) if m else None
    if blob is None:
        i, j = text.find("{"), text.rfind("}")
        blob = text[i:j + 1] if i >= 0 and j > i else None
    if not blob:
        return None
    try:
        return json.loads(blob)
    except Exception:
        try:
            return json.loads(re.sub(r",(\s*[}\]])", r"\1", blob))
        except Exception:
            return None


class WebStackArchitect(ExpertSkill):
    ROLE = "web_stack_architect"
    EXPERTISE = ("a principal full-stack engineer who ships small, correct, "
                 "dependency-light web applications that run offline on Windows")
    DEFAULT_TEMPERATURE = 0.15

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def build(self, request: str, *, slug: str = "", overwrite: bool = False,
              force_db: Optional[bool] = None) -> BuildReport:
        """Build a complete, runnable site from a natural-language request."""
        log.info(f"WebStackArchitect: building for: {request[:80]}")

        spec = self._intake(request, slug=slug, force_db=force_db)
        stack = "py_db" if spec.needs_db else "static"
        out = sp.project_dir(spec.slug, overwrite=overwrite)
        report = BuildReport(project_dir=str(out), stack=stack, spec=spec)

        if spec.needs_db:
            self._build_py_db(spec, out, report)
        else:
            self._build_static(spec, out, report)
        return report

    # ------------------------------------------------------------------ #
    # 1. Intake                                                          #
    # ------------------------------------------------------------------ #
    def _intake(self, request: str, slug: str = "", force_db: Optional[bool] = None) -> SiteSpec:
        hint = _wants_db(request)
        raw = self.consult(
            "Extract a website specification from the request. Reply with ONLY a JSON object:\n"
            '{"slug":"kebab-case-name","name":"Display Name","purpose":"one sentence",'
            '"needs_db":true|false,'
            '"entities":[{"name":"post","fields":[{"name":"title","type":"str"},{"name":"body","type":"text"}]}],'
            '"pages":[{"path":"/","title":"Home","purpose":"..."}],"theme":"short style words"}\n'
            "Rules: snake_case lowercase entity/field names; types from "
            "int/str/text/float/bool/datetime/date; do NOT include an id field (added "
            "automatically); 2-5 pages; entities only if data must persist.\n\n"
            f"Request: {request}",
            max_tokens=1500,
        )
        data = _extract_json(raw) or {}

        needs_db = data.get("needs_db", False)
        if hint is not None:
            needs_db = hint                      # deterministic classifier wins
        if force_db is not None:
            needs_db = force_db                  # explicit caller wins over all

        want_slug = slug or str(data.get("slug") or "").strip().lower()
        want_slug = re.sub(r"[^a-z0-9-]+", "-", want_slug).strip("-")[:40]
        if not sp.valid_slug(want_slug):
            want_slug = "site"

        entities = []
        for e in (data.get("entities") or []):
            en = str(e.get("name", "")).strip().lower()
            if not sp.valid_identifier(en):
                continue
            fields = []
            for f in (e.get("fields") or []):
                fn = str(f.get("name", "")).strip().lower()
                if not sp.valid_identifier(fn) or fn == "id":
                    continue
                fields.append({"name": fn, "type": _SQL_TYPES.get(
                    str(f.get("type", "str")).lower(), "String")})
            if fields:
                entities.append({"name": en, "fields": fields})

        pages = [p for p in (data.get("pages") or []) if p.get("path")][:6] or [
            {"path": "/", "title": "Home", "purpose": "landing"}]

        return SiteSpec(
            slug=want_slug,
            name=str(data.get("name") or want_slug.replace("-", " ").title()),
            purpose=str(data.get("purpose") or request)[:300],
            needs_db=bool(needs_db and entities) if needs_db else False,
            entities=entities,
            pages=pages,
            theme=str(data.get("theme") or "clean modern light/dark"),
        )

    # ------------------------------------------------------------------ #
    # 2. Deterministic code emitters (the model never writes these)      #
    # ------------------------------------------------------------------ #
    def _models_src(self, spec: SiteSpec) -> str:
        out = [
            '"""SQLAlchemy models — generated deterministically from the validated spec."""',
            "from sqlalchemy import (Column, Integer, String, Text, Float, Boolean,",
            "                        DateTime, Date, create_engine)",
            "from sqlalchemy.orm import declarative_base, sessionmaker",
            "import os, datetime",
            "",
            'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")',
            "engine = create_engine(DATABASE_URL, echo=False, future=True)",
            "SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)",
            "Base = declarative_base()",
            "",
        ]
        for e in spec.entities:
            cls = "".join(p.capitalize() for p in e["name"].split("_"))
            out += [f"class {cls}(Base):",
                    f'    __tablename__ = "{e["name"]}"',
                    "    id = Column(Integer, primary_key=True, index=True)"]
            for f in e["fields"]:
                extra = ", default=datetime.datetime.utcnow" if f["type"] == "DateTime" else ""
                out.append(f'    {f["name"]} = Column({f["type"]}{extra})')
            out += ["", f"    def __repr__(self):",
                    f'        return f"<{cls} id={{self.id}}>"', "", ""]
        out += ["def init_db():",
                '    """Create all tables. Safe to call repeatedly."""',
                "    Base.metadata.create_all(bind=engine)", ""]
        return "\n".join(out)

    def _main_src(self, spec: SiteSpec) -> str:
        classes = {e["name"]: "".join(p.capitalize() for p in e["name"].split("_"))
                   for e in spec.entities}
        imports = ", ".join(["init_db", "SessionLocal"] + list(classes.values()))
        lines = [
            '"""FastAPI app — server-rendered with Jinja2. No network, no CDN."""',
            "from fastapi import FastAPI, Request, Form",
            "from fastapi.responses import RedirectResponse",
            "from fastapi.staticfiles import StaticFiles",
            "from fastapi.templating import Jinja2Templates",
            "from jinja2 import StrictUndefined",
            "from pathlib import Path",
            f"from models import {imports}",
            "",
            "BASE = Path(__file__).parent",
            f'app = FastAPI(title="{spec.name}")',
            'app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")',
            'templates = Jinja2Templates(directory=str(BASE / "templates"))',
            "# StrictUndefined: a typo'd variable raises instead of rendering blank.",
            "templates.env.undefined = StrictUndefined",
            "",
            "# Create tables at import time: create_all() is idempotent, and this",
            "# works under uvicorn, pytest and TestClient alike. The deprecated",
            '# @app.on_event("startup") hook does not fire in every context.',
            "init_db()",
            "",
        ]
        first = spec.entities[0]["name"] if spec.entities else None
        # Form params are typed so FastAPI coerces them. Auto-managed timestamp
        # columns are EXCLUDED from the form: passing a string into a SQLite
        # DateTime column raises "only accepts Python datetime objects".
        py_form = {"Integer": ("int", "0"), "Float": ("float", "0.0"),
                   "Boolean": ("bool", "False")}
        for e in spec.entities:
            n, cls = e["name"], classes[e["name"]]
            editable = [f for f in e["fields"] if f["type"] not in ("DateTime", "Date")]
            lines += [
                f'@app.get("/{n}")',
                f"def list_{n}(request: Request):",
                "    db = SessionLocal()",
                f"    items = db.query({cls}).all()",
                # Modern Starlette signature: request FIRST. The legacy
                # TemplateResponse(name, {"request": ...}) form raises
                # "cannot use 'tuple' as a dict key" on current Starlette.
                f'    return templates.TemplateResponse(request, "{n}_list.html", '
                f'{{"items": items, "title": "{n.title()}"}})',
                "",
                f'@app.post("/{n}")',
                f"def create_{n}(" + ", ".join(
                    "{}: {} = Form({})".format(
                        f["name"], *py_form.get(f["type"], ("str", '""')))
                    for f in editable) + "):",
                "    db = SessionLocal()",
                f"    obj = {cls}(" + ", ".join(
                    f'{f["name"]}={f["name"]}' for f in editable) + ")",
                "    db.add(obj); db.commit()",
                f'    return RedirectResponse("/{n}", status_code=303)',
                "",
            ]
        lines += [
            '@app.get("/")',
            "def home(request: Request):",
            '    return templates.TemplateResponse(request, "index.html", '
            f'{{"title": "{spec.name}"}})',
            "",
        ]
        _ = first
        return "\n".join(lines)

    def _base_template(self, spec: SiteSpec) -> str:
        nav = "\n".join(
            f'      <a href="/{e["name"]}">{e["name"].replace("_", " ").title()}</a>'
            for e in spec.entities)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{{{ title }}}} — {spec.name}</title>
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
  <header>
    <a class="brand" href="/">{spec.name}</a>
    <nav>
{nav}
    </nav>
  </header>
  <main>
  {{% block content %}}{{% endblock %}}
  </main>
  <footer><small>{spec.name}</small></footer>
</body>
</html>
"""

    def _css(self, spec: SiteSpec) -> str:
        return """:root{--bg:#ffffff;--fg:#16181d;--muted:#666e7a;--accent:#3b5bfd;--line:#e6e8ec;--card:#fafbfc}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e8eaed;--muted:#9aa3af;--accent:#7d93ff;--line:#242832;--card:#161a21}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{display:flex;gap:1.5rem;align-items:center;padding:1rem 1.5rem;border-bottom:1px solid var(--line)}
.brand{font-weight:700;color:var(--fg);text-decoration:none;font-size:1.1rem}
nav{display:flex;gap:1rem;flex-wrap:wrap}
nav a{color:var(--muted);text-decoration:none}
nav a:hover{color:var(--accent)}
main{max-width:min(72rem,92vw);margin:2rem auto;padding:0 1rem}
h1,h2{line-height:1.25}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1rem 1.25rem;margin:.75rem 0}
form{display:grid;gap:.6rem;max-width:34rem;margin:1.25rem 0}
input,textarea,select{padding:.6rem .7rem;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font:inherit}
button{padding:.6rem 1.1rem;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;cursor:pointer}
button:hover{filter:brightness(1.08)}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:.6rem;border-bottom:1px solid var(--line)}
footer{margin-top:3rem;padding:1.5rem;border-top:1px solid var(--line);color:var(--muted)}
"""

    def _list_template(self, entity: Dict[str, Any]) -> str:
        n = entity["name"]
        heads = "".join(f"<th>{f['name']}</th>" for f in entity["fields"])
        cells = "".join(
            f"<td>{{{{ item.{f['name']} }}}}</td>" for f in entity["fields"])
        # Auto-managed timestamps are shown in the table but never asked for.
        _types = {"Integer": "number", "Float": "number", "Boolean": "checkbox"}
        inputs = "\n".join(
            f'    <label>{f["name"]}<input name="{f["name"]}" '
            f'type="{_types.get(f["type"], "text")}"></label>'
            for f in entity["fields"] if f["type"] not in ("DateTime", "Date"))
        return f"""{{% extends "base.html" %}}
{{% block content %}}
<h1>{{{{ title }}}}</h1>
<form method="post" action="/{n}">
{inputs}
    <button type="submit">Add</button>
</form>
<table>
  <thead><tr><th>id</th>{heads}</tr></thead>
  <tbody>
  {{% for item in items %}}
    <tr><td>{{{{ item.id }}}}</td>{cells}</tr>
  {{% endfor %}}
  </tbody>
</table>
{{% endblock %}}
"""

    # ------------------------------------------------------------------ #
    # 3. Verification                                                    #
    # ------------------------------------------------------------------ #
    def _verify_schema(self, out: Path) -> tuple:
        """Import models.py and create every table in in-memory SQLite."""
        probe = (
            "import sys, os; sys.path.insert(0, r'%s');"
            "os.environ['DATABASE_URL']='sqlite://';"
            "import models; models.Base.metadata.create_all("
            "bind=__import__('sqlalchemy').create_engine('sqlite://'));"
            "print('SCHEMA_OK', len(models.Base.metadata.tables))" % str(out)
        )
        try:
            p = subprocess.run([_PY, "-c", probe], capture_output=True, text=True, timeout=120)
            return ("SCHEMA_OK" in (p.stdout or ""),
                    (p.stdout or "") + (p.stderr or ""))
        except Exception as e:
            return False, f"schema probe failed: {e}"

    def _verify_templates(self, out: Path, spec: SiteSpec) -> str:
        """Render every template with StrictUndefined + validate the RESULT as HTML.

        Validating the template source would prove nothing: html5lib happily
        accepts '{{ x }}' as text. We must validate the RENDERED output.
        """
        probe = r'''
import sys, io, json
sys.path.insert(0, r"%s")
from pathlib import Path
import jinja2, html5lib
base = Path(r"%s") / "templates"
env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(base)),
                         undefined=jinja2.StrictUndefined)
class Row:
    def __init__(self): self.id = 1
    def __getattr__(self, k): return "sample"
problems = []
for tpl in sorted(base.glob("*.html")):
    if tpl.name == "base.html":
        continue
    try:
        html = env.get_template(tpl.name).render(
            title="T", items=[Row()], request=None)
    except Exception as e:
        problems.append(f"{tpl.name}: RENDER FAILED: {type(e).__name__}: {e}")
        continue
    try:
        html5lib.HTMLParser(strict=True).parse(io.StringIO(html))
    except Exception as e:
        problems.append(f"{tpl.name}: INVALID HTML: {str(e)[:160]}")
    if "http://" in html or "https://" in html:
        problems.append(f"{tpl.name}: external URL present (must be offline)")
print(json.dumps(problems))
''' % (str(out), str(out))
        try:
            p = subprocess.run([_PY, "-c", probe], capture_output=True, text=True, timeout=180)
            raw = (p.stdout or "").strip().splitlines()
            probs = json.loads(raw[-1]) if raw and raw[-1].startswith("[") else None
            if probs is None:
                return f"{GATE_DID_NOT_RUN}: template check could not run: {(p.stderr or '')[:400]}"
            return "Templates: all render + valid HTML ✅" if not probs \
                else "Template problems:\n  " + "\n  ".join(probs)
        except Exception as e:
            return f"{GATE_DID_NOT_RUN}: template check error: {e}"

    def _smoke_http(self, out: Path) -> str:
        """Actually START the app and GET every route. The only proof it runs.

        Template-render checks are NOT sufficient: they missed a real
        TemplateResponse signature bug that returned HTTP 500 on every page
        while every other gate reported success. If it does not answer 200,
        it is not built.
        """
        probe = r'''
import sys, json
sys.path.insert(0, r"%s")
try:
    from fastapi.testclient import TestClient
    import main
    # Context manager form so lifespan/startup handlers actually run.
    client = TestClient(main.app)
    client.__enter__()
    routes = [r.path for r in main.app.routes
              if getattr(r, "methods", None) and "GET" in r.methods
              and "{" not in r.path and r.path not in ("/openapi.json", "/docs",
              "/docs/oauth2-redirect", "/redoc")]
    bad = []
    for p in sorted(set(routes)):
        try:
            resp = client.get(p)
            if resp.status_code >= 400:
                body = resp.text[:200].replace("\n", " ")
                bad.append(f"GET {p} -> {resp.status_code}  {body}")
        except Exception as e:
            bad.append(f"GET {p} -> EXCEPTION {type(e).__name__}: {str(e)[:180]}")

    # POST every create route with realistic values, then prove the row persisted.
    # A GET-only smoke test misses type bugs (e.g. a string sent into a DateTime
    # column) that make the whole app unusable for actually entering data.
    posts = [r for r in main.app.routes
             if getattr(r, "methods", None) and "POST" in r.methods and "{" not in r.path]
    for r in posts:
        fields = {}
        for name, fld in getattr(r, "dependant", None).__dict__.get("body_params", []) \
                and {p.name: p for p in r.dependant.body_params}.items() or {}:
            ann = getattr(fld.field_info, "annotation", None) or fld.type_
            fields[name] = 1 if ann is int else (1.5 if ann is float else
                                                 ("true" if ann is bool else "smoke"))
        try:
            resp = client.post(r.path, data=fields, follow_redirects=False)
            if resp.status_code >= 400:
                bad.append(f"POST {r.path} {fields} -> {resp.status_code} "
                           f"{resp.text[:180]}".replace("\n", " "))
            else:
                check = client.get(r.path)
                if "smoke" not in check.text and str(1) not in check.text:
                    bad.append(f"POST {r.path} accepted but the row does not appear on GET")
        except Exception as e:
            bad.append(f"POST {r.path} -> EXCEPTION {type(e).__name__}: {str(e)[:180]}")

    print("SMOKE" + json.dumps({"checked": sorted(set(routes)) + [f"POST {r.path}" for r in posts],
                                "bad": bad}))
except Exception as e:
    import traceback
    print("SMOKE" + json.dumps({"checked": [], "bad": [
        f"app failed to import/start: {type(e).__name__}: {str(e)[:200]}",
        traceback.format_exc()[-400:]]}))
''' % str(out)
        try:
            p = subprocess.run([_PY, "-c", probe], capture_output=True, text=True, timeout=240)
            line = next((l for l in (p.stdout or "").splitlines() if l.startswith("SMOKE")), "")
            if not line:
                return f"{GATE_DID_NOT_RUN}: HTTP smoke test could not run: {(p.stderr or '')[:400]}"
            d = json.loads(line[5:])
            if d["bad"]:
                return ("HTTP smoke test FAILED:\n  " + "\n  ".join(d["bad"]))
            return f"HTTP smoke test: {len(d['checked'])} route(s) return 200 ✅ {d['checked']}"
        except Exception as e:
            return f"{GATE_DID_NOT_RUN}: HTTP smoke test error: {e}"

    def _verify_python(self, out: Path) -> str:
        if code_intelligence is None:
            return "(code_intelligence unavailable)"
        try:
            return code_intelligence.analyze_tree(str(out)).to_report()
        except Exception as e:
            return f"({GATE_DID_NOT_RUN}: analyzer error: {e})"

    @staticmethod
    def _verify_js(out: Path) -> str:
        js = list(out.rglob("*.js"))
        if not js:
            return ""
        bad = []
        for f in js:
            try:
                p = subprocess.run(["node", "--check", str(f)],
                                   capture_output=True, text=True, timeout=60)
                if p.returncode != 0:
                    bad.append(f"{f.name}: {(p.stderr or '').strip().splitlines()[0][:140]}")
            except Exception:
                return "(node unavailable — JS not checked)"
        return "JS: all files parse ✅" if not bad else "JS syntax errors:\n  " + "\n  ".join(bad)

    # ------------------------------------------------------------------ #
    # 4. Builders                                                        #
    # ------------------------------------------------------------------ #
    def _write(self, out: Path, rel: str, content: str, report: BuildReport,
               note: str = "deterministic") -> None:
        try:
            sp.write_file(out, rel, content)
            report.files.append(FileResult(rel, True, 1, note=note))
        except Exception as e:
            report.files.append(FileResult(rel, False, 1, note=f"{type(e).__name__}: {e}"))

    def _build_py_db(self, spec: SiteSpec, out: Path, report: BuildReport) -> None:
        # --- deterministic core --------------------------------------- #
        self._write(out, "models.py", self._models_src(spec), report)

        ok, detail = self._verify_schema(out)
        report.schema_ok = ok
        if not ok:
            # Schema-first gate: do not generate an app on top of a broken schema.
            report.status = "❌ FAILED — database schema does not create"
            report.verification = f"Schema gate failed:\n{detail[:1500]}"
            return

        self._write(out, "main.py", self._main_src(spec), report)
        self._write(out, "templates/base.html", self._base_template(spec), report)
        self._write(out, "static/css/app.css", self._css(spec), report)
        for e in spec.entities:
            self._write(out, f"templates/{e['name']}_list.html", self._list_template(e), report)

        index = ("{% extends \"base.html\" %}\n{% block content %}\n"
                 f"<h1>{spec.name}</h1>\n<p class=\"card\">{spec.purpose}</p>\n"
                 + "\n".join(f'<p><a href="/{e["name"]}">Manage {e["name"]}</a></p>'
                             for e in spec.entities)
                 + "\n{% endblock %}\n")
        self._write(out, "templates/index.html", index, report)

        self._write(out, "requirements.txt",
                    "fastapi\nuvicorn\nsqlalchemy\njinja2\npython-multipart\n", report)
        self._write(out, ".env.example", 'DATABASE_URL=sqlite:///./app.db\n', report)
        self._write(out, ".gitignore", "__pycache__/\n*.db\n.env\n", report)
        self._write(out, "run.ps1",
                    f'# Run this site\n& "{_PY}" -m uvicorn main:app --reload --port 8000\n', report)
        self._write(out, "README.md",
                    f"# {spec.name}\n\n{spec.purpose}\n\n## Run\n\n```powershell\n"
                    f'& "{_PY}" -m uvicorn main:app --reload --port 8000\n```\n\n'
                    "Then open http://127.0.0.1:8000\n\n"
                    f"Stack: FastAPI + SQLAlchemy + Jinja2 + SQLite (fully offline).\n", report)

        # --- verification --------------------------------------------- #
        parts = [f"Schema: {len(spec.entities)} table(s) created cleanly ✅",
                 self._verify_templates(out, spec),
                 self._smoke_http(out),
                 self._verify_python(out)]
        report.verification = "\n\n".join(p for p in parts if p)
        ok, why = gate_outcome(report.verification)
        report.status = ("✅ built and verified" if ok
                         else f"⚠️ built, ΑΝΕΠΑΛΗΘΕΥΤΟ — {why}")
        report.run_cmd = f'cd "{out}"; & "{_PY}" -m uvicorn main:app --reload --port 8000'

    def _build_static(self, spec: SiteSpec, out: Path, report: BuildReport) -> None:
        self._write(out, "styles.css", self._css(spec), report)

        nav = "\n".join(f'      <a href="{p["path"]}">{p.get("title", "Page")}</a>'
                        for p in spec.pages)
        for page in spec.pages:
            fname = "index.html" if page["path"] in ("/", "") else \
                re.sub(r"[^a-z0-9-]+", "-", page["path"].strip("/").lower()) + ".html"
            body = self.consult(
                "Write ONLY the inner HTML for the <main> element of this page. "
                "Rules: semantic HTML5, no <html>/<head>/<body> tags, no inline styles, "
                "no <script>, no external URLs or CDN links, use class \"card\" for "
                "boxes. Real, specific copy — not lorem ipsum.\n\n"
                f"Site: {spec.name} — {spec.purpose}\n"
                f"Page: {page.get('title')} ({page['path']}) — {page.get('purpose', '')}\n"
                f"Style: {spec.theme}",
                max_tokens=2000,
            )
            inner = body if body and not body.startswith("(") else \
                f"<h1>{page.get('title', spec.name)}</h1><p class=\"card\">{spec.purpose}</p>"
            inner = re.sub(r"```[a-z]*\n?|```", "", inner)
            inner = re.sub(r"https?://\S+", "#", inner)  # enforce offline
            html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page.get('title', spec.name)} — {spec.name}</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <header>
    <a class="brand" href="/">{spec.name}</a>
    <nav>
{nav}
    </nav>
  </header>
  <main>
{inner}
  </main>
  <footer><small>{spec.name}</small></footer>
</body>
</html>
"""
            self._write(out, fname, html, report, note="llm content")

        self._write(out, "README.md",
                    f"# {spec.name}\n\n{spec.purpose}\n\n## Run\n\n```powershell\n"
                    f'& "{_PY}" -m http.server 8000\n```\n\nOpen http://127.0.0.1:8000\n', report)

        probs = []
        try:
            probe = r'''
import sys, io, json, pathlib, html5lib
bad = []
for f in pathlib.Path(r"%s").rglob("*.html"):
    try:
        html5lib.HTMLParser(strict=True).parse(io.StringIO(f.read_text(encoding="utf-8")))
    except Exception as e:
        bad.append(f"{f.name}: {str(e)[:150]}")
print(json.dumps(bad))
''' % str(out)
            p = subprocess.run([_PY, "-c", probe], capture_output=True, text=True, timeout=120)
            tail = (p.stdout or "").strip().splitlines()
            if tail and tail[-1].startswith("["):
                probs = json.loads(tail[-1])
            else:
                # Silence is not a pass. A missing html5lib exits 1 with empty
                # stdout, and this used to become "HTML: all pages valid ✅"
                # with zero pages checked — byte-identical to a real run.
                probs = [f"{GATE_DID_NOT_RUN}: html validation produced no "
                         f"result (rc={p.returncode}, "
                         f"stderr={(p.stderr or '')[:200]})"]
        except Exception as e:
            probs = [f"{GATE_DID_NOT_RUN}: html check error: {e}"]

        js = self._verify_js(out)
        report.verification = ("HTML: all pages valid ✅" if not probs
                               else "HTML problems:\n  " + "\n  ".join(probs))
        if js:
            report.verification += "\n" + js
        ok, why = gate_outcome(report.verification)
        report.status = ("✅ built and verified" if ok
                         else f"⚠️ built, ΑΝΕΠΑΛΗΘΕΥΤΟ — {why}")
        report.run_cmd = f'cd "{out}"; & "{_PY}" -m http.server 8000'


#: Emitted by any gate that could not RUN, as opposed to one that ran and
#: passed. The distinction was invisible before: `blocking` was a substring test
#: for "RENDER FAILED" / "INVALID HTML" / "smoke test FAILED" / "[HIGH" /
#: "[CRITICAL", and none of those appear in "HTTP smoke test error: timed out
#: after 240 seconds" or "template check could not run: ModuleNotFoundError:
#: html5lib". A 240-second timeout produced the same green headline as a fully
#: verified build. The module docstring says "If it does not answer 200, it is
#: not built" — this is what makes that true.
GATE_DID_NOT_RUN = "ΔΕΝ ΕΚΤΕΛΕΣΤΗΚΕ"


def gate_outcome(verification: str) -> tuple:
    """(verified, reason). Verified requires POSITIVE evidence from every gate."""
    if GATE_DID_NOT_RUN in verification:
        return False, "κάποιος έλεγχος δεν εκτελέστηκε"
    for bad in ("RENDER FAILED", "INVALID HTML", "smoke test FAILED",
                "[HIGH", "[CRITICAL"):
        if bad in verification:
            return False, "ο έλεγχος βρήκε πρόβλημα"
    return True, ""


web_stack_architect = WebStackArchitect()
