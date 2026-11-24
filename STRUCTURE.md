# Project Structure

How the GitLab clone is organised, what goes where, and how a request flows through the code.
Read this before adding a new app, model, endpoint or page.

```
gitlab/                      ← git repo root
├── README.md
├── STRUCTURE.md             ← this file
├── .gitignore
├── src/                     ← Django backend (API + git server)
└── client/                  ← React frontend (Vite + TypeScript)
```

---

## 1. Backend (`src/`)

### 1.1 Full layout (target)

`✅` = exists today · everything else is added as you reach that phase in `TODO.md`.

```
src/
├── manage.py                          ✅
├── requirements.txt                   ✅
├── TODO.md                            ✅
│
├── gitlab/                            ✅ Project config (settings, root URLs). No business logic here.
│   ├── settings.py                    ✅  (later: split into settings/base.py, dev.py, prod.py)
│   ├── urls.py                        ✅  Root router: /admin/, /api/v1/, git HTTP routes
│   ├── api_urls.py                       Collects every app's api/urls.py under /api/v1/
│   ├── asgi.py / wsgi.py              ✅
│   ├── .env                           ✅  (ignored — real secrets)
│   └── .env.example                   ✅
│
├── core/                              ✅ Shared building blocks. Depends on NO other local app.
├── accounts/                          ✅ Users, auth, PATs, SSH keys
├── namespaces/                           User/group namespaces, groups, group members
├── repositories/                      ✅ Projects, project members, git storage on disk
├── git_http/                             Smart-HTTP git server (clone / fetch / push)
├── issues/                               Issues, labels, milestones
├── merge_requests/                       MRs, diffs, approvals, merging
├── notes/                                Comments shared by issues & MRs
├── activity/                             Events, activity feed, to-dos
├── webhooks/                             Project webhooks + delivery log
│
├── media/                             (ignored) uploads — avatars, attachments
└── repos/                             (ignored) bare git repositories: repos/<namespace>/<project>.git
```

### 1.2 Dependency direction (very important)

Apps may only import from apps **to their left**. Never import "backwards" — it creates circular imports.

```
core  ←  accounts  ←  namespaces  ←  repositories  ←  git_http
                                                  ←  issues  ←  merge_requests
                                                  ←  notes / activity / webhooks
```

- `core` imports nothing from local apps.
- `accounts` may use `core` only.
- `repositories` may use `core`, `accounts`, `namespaces`.
- If two apps need to talk "backwards" (e.g. a push must create an activity event), use **Django signals** or a **service function in the higher app**, not a direct import.

---

## 2. The `core` app — what it is and what goes in it

`core` is **not a feature**. It holds the reusable foundation every other app builds on:
base models, the API response format, error handling, pagination, base permissions, helpers.

**Rule:** if code is used by 2+ apps and knows nothing about users/projects/issues → it belongs in `core`.
If it mentions a specific feature (e.g. "project", "issue") → it belongs in that feature's app.

```
core/
├── __init__.py
├── apps.py
├── admin.py                 Shared admin mixins (e.g. read-only timestamps)
│
├── models/
│   ├── __init__.py          Exports the base classes
│   ├── base.py         ✅   BaseAbstractModel: UUID id, is_active, created_at, updated_at
│   └── mixins.py            SoftDeleteMixin (deleted_at), OrderedMixin, etc.
│
├── api/
│   ├── responses.py         success_response() / error_response() — ONE response shape for the API
│   ├── exceptions.py        custom_exception_handler + AppError classes (NotFound, Forbidden, Conflict…)
│   ├── pagination.py        StandardPagination (page, page_size, total, results)
│   ├── permissions.py       Generic DRF permissions (IsAdmin, IsOwnerOrReadOnly, IsActiveUser)
│   ├── authentication.py    JWT auth that checks token_version + user state
│   ├── serializers.py       BaseModelSerializer (common read-only fields)
│   └── views.py             BaseAPIView / mixins that wrap responses consistently
│
├── constants.py             AccessLevel (10/20/30/40/50), Visibility (private/internal/public), RESERVED_NAMES
├── validators.py            Shared validators: path/slug (username, group, project), file size
├── utils/
│   ├── text.py              slugify_path(), markdown rendering
│   ├── time.py              Timezone helpers
│   └── files.py             Safe file / path helpers (prevent ../ traversal)
│
├── management/commands/     Project-wide commands (e.g. seed_dev_data)
├── migrations/
└── tests/
```

### 2.1 Example: one response shape for the whole API

`core/api/responses.py` — `ApiResponse` (built ✅)
```python
from core.api.responses import ApiResponse

return ApiResponse.success("Project created", data=serializer.data, status=201)
return ApiResponse.error("Project not found", status=404)
# list views get this automatically via StandardPagination:
return ApiResponse.pagination("", paginator, data)
```

Every response has the same keys:
```json
{ "success": true,  "status": 200, "message": "", "data": { ... }, "errors": null, "metadata": null }
{ "success": false, "status": 400, "message": "Validation failed.", "data": null,
  "errors": { "email": ["Enter a valid email address."] }, "metadata": null }
```
Paginated lists add:
```json
"pagination": { "count": 42, "page_size": 20, "total_pages": 3, "current_page": 1,
                "next_page": "http://…?page=2", "previous_page": null }
```

Also built ✅ and registered in `REST_FRAMEWORK` settings:
- `core/api/exceptions.py` — `custom_exception_handler` turns every error (validation, 401, 403, 404,
  unexpected 500s) into the `ApiResponse.error` shape. Raise `AppError(message, status_code=…, errors=…)`
  for expected business errors.
- `core/api/pagination.py` — `StandardPagination` (`?page=` & `?page_size=`, default 20, max 100).
- `core/api/authentication.py` — `TokenVersionJWTAuthentication` rejects revoked tokens and inactive users.
  Always log users in with `issue_tokens_for_user(user)`.

The frontend only ever has to handle one format.

### 2.2 Example: shared constants

`core/constants.py`
```python
from django.db import models


class AccessLevel(models.IntegerChoices):
    GUEST = 10, "Guest"
    REPORTER = 20, "Reporter"
    DEVELOPER = 30, "Developer"
    MAINTAINER = 40, "Maintainer"
    OWNER = 50, "Owner"


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    INTERNAL = "internal", "Internal"
    PUBLIC = "public", "Public"
```

> Today `RESERVED_USERNAMES` and the username validator live in `accounts/models/user.py`.
> Move them to `core/constants.py` + `core/validators.py` when building groups/projects,
> because group and project paths need the same rules.

---

## 3. Layout of a feature app

Every feature app (`accounts`, `repositories`, `issues`, …) uses the **same** layout,
so you always know where to look.

```
<app>/
├── __init__.py
├── apps.py
├── admin.py                 Django admin for this app's models
│
├── models/                  One file per model, exported from __init__.py
│   ├── __init__.py
│   └── <model>.py
│
├── api/
│   ├── urls.py              Routes for this app (included under /api/v1/)
│   ├── views.py             Thin views: auth/permission → serializer → service → response
│   ├── serializers.py       Input validation + output shape. No DB writes beyond simple create/update.
│   └── permissions.py       Feature permissions (e.g. CanPushToProject)
│
├── services.py              WRITE business logic: create_project(), block_user(), merge_mr()
├── selectors.py             READ logic / complex queries: projects_visible_to(user), user_feed(user)
├── signals.py               React to events from other apps (connected in apps.py ready())
├── tasks.py                 Background jobs (later: Celery)
├── constants.py             Choices/enums used only by this app
├── exceptions.py            Errors specific to this app
│
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_services.py
    └── test_api.py
```

Grow into this: start with only the files you need, add the others when that need appears.
For example, `selectors.py` only appears once queries get complex.

### 3.1 What each layer may do

| Layer | Does | Must NOT |
|---|---|---|
| `models/` | Fields, constraints, small helpers on one object (`is_bot`, `__str__`) | Call git, send emails, touch other apps' models in `save()` |
| `serializers.py` | Validate input, shape output | Contain business rules, call git |
| `api/views.py` | Auth, permission, call serializer + service, return `success_response` | Contain business logic or raw queries |
| `services.py` | Business rules, transactions, git operations, emit events | Know about HTTP / `request` objects |
| `selectors.py` | Read queries with permission filtering | Write to the DB |
| `signals.py` | Glue between apps | Hold important logic (hard to trace — keep small) |

Why services? The same logic gets used from the API, the admin, management commands,
git hooks and tests. If the logic lives in a view, only the API can use it.

---

## 4. How a request flows

### 4.1 API request: `POST /api/v1/projects/` (create project)

```
Client (React)
   │  Authorization: Bearer <JWT>
   ▼
gitlab/urls.py  →  gitlab/api_urls.py  →  repositories/api/urls.py
   ▼
core/api/authentication.py     JWT valid? token_version matches? user.state == active?
   ▼
repositories/api/views.py      ProjectCreateView
   │  permission: IsAuthenticated + user.can_create_project
   ▼
repositories/api/serializers.py  ProjectCreateSerializer → validates name/path/visibility
   ▼
repositories/services.py       create_project(user, namespace, **data)
   │  ├─ check projects_limit
   │  ├─ transaction.atomic(): save Project + ProjectMember(owner)
   │  ├─ git init --bare repos/<ns>/<path>.git      (repositories/git/…)
   │  └─ emit "project_created" → activity app records an Event
   ▼
views.py returns success_response(ProjectSerializer(project).data, status=201)
   ▼
On any error → core/api/exceptions.py → error_response(...) in the standard shape
```

### 4.2 Git request: `git push http://host/root/demo.git`

```
git client
   ▼
gitlab/urls.py  →  git_http/urls.py   (/<namespace>/<project>.git/...)
   ▼
git_http/auth.py        HTTP Basic: username+password OR personal access token
   ▼
git_http/views.py       look up Project, check AccessLevel (read for clone, Developer+ for push)
   ▼
git_http/backend.py     stream to `git http-backend` / `git receive-pack`
   ▼
git hooks (pre-receive: protected branches; post-receive: record push event, update MRs)
```

### 4.3 Where git code lives

```
repositories/
└── git/
    ├── storage.py      repo path on disk, create/move/delete bare repos
    ├── reader.py       branches, tags, tree, blob, commits, diff (GitPython)
    └── writer.py       create branch/tag, commit a file from the web editor
```
Views never call GitPython directly — they call `services.py` / `selectors.py`, which use `git/`.

---

## 5. Frontend (`client/`)

Organised **by feature**, mirroring the backend apps.

```
client/
├── index.html
├── package.json / pnpm-lock.yaml
├── vite.config.ts
├── .env.example                 VITE_API_URL=http://127.0.0.1:8000/api/v1
└── src/
    ├── main.tsx                 Entry: renders <App/> with providers
    ├── App.tsx                  Router outlet
    │
    ├── app/                     App-wide setup
    │   ├── router.tsx           All routes (/:namespace/:project/-/tree/:ref/*)
    │   ├── providers.tsx        Query client, auth provider, theme
    │   └── layout/              Shell: top bar, sidebar, page layout
    │
    ├── api/                     The ONLY place that talks HTTP
    │   ├── client.ts            fetch/axios instance, base URL, JWT header, auto-refresh on 401
    │   └── types.ts             ApiResponse<T> matching core/api/responses.py
    │
    ├── features/                One folder per backend app
    │   ├── auth/                login, register, useAuth()
    │   │   ├── api.ts           login(), register(), refresh()
    │   │   ├── pages/           LoginPage.tsx, RegisterPage.tsx
    │   │   ├── components/
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── users/               profile, settings, SSH keys, PATs
    │   ├── groups/
    │   ├── projects/            project home, file tree, file viewer, commits, branches
    │   ├── issues/
    │   ├── merge-requests/
    │   └── admin/
    │
    ├── components/              Shared, feature-agnostic UI
    │   ├── ui/                  Button, Input, Modal, Badge, Avatar, Tabs
    │   └── common/              Markdown, CodeBlock, DiffView, Pagination, EmptyState
    │
    ├── hooks/                   Generic hooks (useDebounce, usePagination)
    ├── lib/                     Helpers (formatDate, cn(), constants)
    ├── styles/                  Global CSS / tokens
    └── assets/
```

**Rules**
- Components never call `fetch` directly — they use `features/<x>/api.ts`, which uses `api/client.ts`.
- A feature may import from `components/`, `hooks/`, `lib/`, `api/` — **not** from another feature's internals.
  If two features need it, move it to `components/` (the frontend equivalent of `core`).

---

## 6. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Django app | plural, snake_case | `merge_requests` |
| Model | singular, PascalCase | `MergeRequest`, `ProjectMember` |
| Model file | singular, snake_case | `models/merge_request.py` |
| Service function | verb_noun | `create_project()`, `merge_merge_request()` |
| Selector function | noun_description | `projects_visible_to(user)` |
| API URL | plural, kebab-case, versioned | `/api/v1/projects/<id>/merge-requests/` |
| Serializer | `<Model><Action>Serializer` | `ProjectCreateSerializer`, `ProjectDetailSerializer` |
| React component | PascalCase file | `ProjectCard.tsx` |
| React hook | `use` + camelCase | `useProject()` |

---

## 7. Checklist: adding a new feature

1. Does it belong to an existing app? If not, `python manage.py startapp <name>`, then convert to the layout in §3.
2. Model in `models/<model>.py`, inheriting `core.models.BaseAbstractModel`; export it in `models/__init__.py`.
3. `makemigrations` → `migrate` (migrations are not committed — see `.gitignore`).
4. Register in `admin.py`.
5. Business logic in `services.py` (writes) / `selectors.py` (reads).
6. `serializers.py` → `api/views.py` → `api/urls.py`; include it in `gitlab/api_urls.py`.
7. Return `success_response` / raise `core` errors — never build a custom response shape.
8. Tests in `tests/` (service + API).
9. Frontend: `features/<name>/api.ts` → `pages/` → add route in `app/router.tsx`.
10. Tick it off in `src/TODO.md`.
