"""One table of every page locator and URL path the acceptance suite uses (SPEC-04).

Selectors were written against the upstream GakuNin RDM UI (RDM-osf.io, legacy Knockout pages plus
fakecas) without a running instance. Every entry marked TODO(M2) must be verified on the real app
once `grdm-dev install --profile core` is green; change them here only, never in test files.

Rules: prefer ARIA roles / visible text over CSS classes; never hard-code a port (ports come from
runtime/.env through conftest.base_url / conftest.ports).
"""
from __future__ import annotations

# --- URL paths (relative to base_url = web service) -----------------------------------------------
PATHS = {
    "login": "/login/",                   # web redirects here when a session is missing
    "dashboard": "/dashboard/",
    "my_projects": "/myprojects/",
    "logout": "/logout/",
    "new_project": "/dashboard/",         # the "Create new project" button lives on the dashboard
    "institutions_admin": "/institutions/",  # TODO(M2): the admin app (port 8001) path for institution users
}

API = {
    "me": "/v2/users/me/",
    "nodes": "/v2/nodes/",
    "node": "/v2/nodes/{node_id}/",
    "node_files": "/v2/nodes/{node_id}/files/osfstorage/",
    "node_wikis": "/v2/nodes/{node_id}/wikis/",
    "node_contributors": "/v2/nodes/{node_id}/contributors/",
    "institution_users": "/v2/institutions/{institution_id}/users/",  # TODO(M2): confirm the admin-only listing path
}

WATERBUTLER = {
    # waterbutler v1: PUT ?kind=file&name=<name> uploads into the root of a provider
    "upload": "/v1/resources/{node_id}/providers/osfstorage/?kind=file&name={name}",
    "download": "/v1/resources/{node_id}/providers/osfstorage{path}",
}

MFR = {
    "render": "/render?url={file_url}",  # TODO(M2): confirm the exact render URL the web app embeds
}

ADMIN = {
    "login": "/account/login/",            # TODO(M2): Django admin app login path
    "institution_users": "/institutions/{institution_id}/users/",  # TODO(M2): confirm
}

# --- fakecas login form (upstream README: any username, password = the user's e-mail) -------------
FAKECAS = {
    "username": "input[name='username']",      # verified on the real fakecas page (acceptance run 5, M2)
    "password": "input[name='password']",      # present but inside <section hidden>: fakecas needs no password
    "submit": "button[type='submit'], input[type='submit']",
}

# --- web (legacy Knockout UI) ---------------------------------------------------------------------
WEB = {
    "dashboard_heading": "text=My Projects",                    # TODO(M2): confirm dashboard landing text
    "user_menu": "#secondary-navigation",                       # TODO(M2): nav bar showing the user name
    "create_project_button": "button:has-text('Create new project'), a:has-text('Create new project')",
    "create_project_title": "input#projectName, input[name='title']",  # TODO(M2)
    "create_project_submit": "button:has-text('Create')",
    "project_title": "#nodeTitleEditable, h2#nodeTitle",       # TODO(M2)
    "files_tab": "a:has-text('Files')",
    "wiki_tab": "a:has-text('Wiki')",
    "wiki_edit_button": "a:has-text('Edit'), button:has-text('Edit')",
    "wiki_editor": ".CodeMirror textarea, textarea#editor",     # TODO(M2): wiki editor widget (sharejs/CodeMirror)
    "wiki_rendered": "#wikiViewRender, .wiki-content",          # TODO(M2)
    "file_preview_iframe": "iframe#mfrIframe, iframe[src*='render']",  # TODO(M2)
    "error_page": ".error, #error-page, text=Forbidden",
}

ADMIN_UI = {
    "login_user": "input[name='username'], input[name='email']",  # TODO(M2)
    "login_pass": "input[name='password']",
    "login_submit": "button[type='submit'], input[type='submit']",
    "institution_user_table": "table",                          # TODO(M2): institution users list
}
