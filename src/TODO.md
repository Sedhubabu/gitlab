# GitLab Clone — Build Roadmap

Stack: Django 5.2 + DRF + SimpleJWT (API) · GitPython / `git` CLI (repos on disk) · React (frontend) · SQLite → Postgres.

Work top to bottom: each phase builds on the one before it. Each phase ends with a **Done when** check.

---

## Phase 0 — Foundation
- [x] Django project, apps: `core`, `accounts`, `repositories`
- [x] `BaseAbstractModel` (UUID id, is_active, timestamps)
- [x] Settings from `.env` (SECRET_KEY, DEBUG, hosts, DATABASE_URL, CORS)
- [x] DRF + JWT defaults, CORS middleware, auditlog
- [x] GitLab-style `User` model + manager (username/email login)
- [x] User admin (filters, state actions, audit log)
- [X] Run `makemigrations` + `migrate`, create superuser
- [X] `git init` the project, add `.gitignore` (venv, db.sqlite3, .env, media/, repos/)
- [X] Add `.env.example` (no real secrets)
- [ ] `core`: standard API response format, custom exception handler, pagination class
- [ ] `core`: `GIT_REPOS_ROOT` setting (where bare repos live on disk)
- [ ] Set up tests (`pytest-django` or Django test runner) + `ruff` for lint

**Done when:** a fresh clone can be set up from the README and `manage.py check` and the tests pass.

---

## Phase 1 — Authentication & Users API
- [ ] `POST /api/auth/register` (username, email, name, password)
- [ ] `POST /api/auth/login` (email **or** username) → access + refresh JWT
- [ ] `POST /api/auth/refresh`, `POST /api/auth/logout` (bump `token_version`)
- [ ] Custom JWT auth class that rejects tokens with an old `token_version` or a non-active `state`
- [ ] Email confirmation (`confirmed_at`), password reset by email
- [ ] `GET/PATCH /api/user` (current user profile, avatar upload)
- [ ] `GET /api/users/<username>` (public profile; respect `private_profile`)
- [ ] Change password, `password_change_required` flow
- [ ] Personal Access Tokens model (name, scopes, expires_at, hashed token, last_used_at)
- [ ] SSH keys model (title, public key, fingerprint) + API
- [ ] Update `current_sign_in_at` / `last_activity_on`

**Done when:** you can register, log in, refresh, log out, and call the API with a PAT.

---

## Phase 2 — Namespaces & Groups
- [ ] `Namespace` model (path, name, kind = user | group, parent for subgroups)
- [ ] Auto-create a personal namespace when a user is created (path = username)
- [ ] `Group` model (name, path, description, visibility, avatar, parent group)
- [ ] `GroupMember` (user, group, access_level, expires_at)
- [ ] Access levels: Guest 10, Reporter 20, Developer 30, Maintainer 40, Owner 50
- [ ] Group CRUD + members API; respect `can_create_group`
- [ ] Path uniqueness across users and groups (shared reserved-name list)

**Done when:** `/<username>` and `/<group>/<subgroup>` both resolve to a namespace.

---

## Phase 3 — Projects (Repositories)
- [ ] `Project` model (namespace, name, path, description, visibility: private/internal/public, default_branch, archived, forked_from)
- [ ] `ProjectMember` (user, project, access_level); inherit group membership
- [ ] On create: `git init --bare <GIT_REPOS_ROOT>/<namespace>/<path>.git`
- [ ] Optional "initialize with README" (first commit on `main`)
- [ ] Rename/transfer project (move the folder on disk + update the path)
- [ ] Delete project (soft delete, then remove from disk)
- [ ] Respect `projects_limit` and `external` users
- [ ] Central permission helper: `can(user, action, project)`
- [ ] Project CRUD + members API, star a project, project list/search

**Done when:** creating a project via the API creates a bare repo on disk.

---

## Phase 4 — Git over HTTP (push / clone)
- [ ] `GET /<ns>/<project>.git/info/refs?service=git-upload-pack|git-receive-pack`
- [ ] `POST /<ns>/<project>.git/git-upload-pack` (clone/fetch)
- [ ] `POST /<ns>/<project>.git/git-receive-pack` (push)
- [ ] Proxy to `git http-backend` (or `git upload-pack --stateless-rpc`) with streaming
- [ ] HTTP Basic auth: username + password **or** PAT
- [ ] Permission checks: read for clone, Developer+ for push
- [ ] Post-receive hook → record push events, update `last_activity_on`

**Done when:** `git clone http://localhost:8000/root/demo.git` and `git push` both work.

---

## Phase 5 — Repository Browsing API
- [ ] Branches: list, create, delete; default branch
- [ ] Tags: list, create, delete
- [ ] Tree: list files at `ref` + `path`
- [ ] Blob: raw file content, size limit, binary detection
- [ ] Commits: list (paginated, filter by path), single commit with diff
- [ ] Compare two refs (`/compare/main...feature`)
- [ ] Blame, file history
- [ ] Download archive (zip/tar.gz)
- [ ] Create/edit/delete a file through the API (web editor commit)
- [ ] Render README.md

**Done when:** the frontend can browse any branch, file and commit.

---

## Phase 6 — Protected Branches & Settings
- [ ] `ProtectedBranch` (name/pattern, who can push, who can merge, allow force push)
- [ ] Enforce in a pre-receive hook (reject push → clear error message)
- [ ] Project settings: visibility, default branch, merge method, archive project
- [ ] Deploy keys / deploy tokens (read-only access)

**Done when:** a Developer can't push to `main` when it's protected.

---

## Phase 7 — Issues
- [ ] `Issue` (project, iid per project, title, description, author, assignees, state open/closed, due_date, confidential)
- [ ] `Label` (project/group), `Milestone`
- [ ] Notes/comments (shared model for issues and MRs), Markdown support
- [ ] Mentions (`@user`, `#123`, `!45`) → links + notifications
- [ ] Filters: state, label, assignee, author, milestone, search
- [ ] Close issue from a commit message (`Closes #12`)

**Done when:** a full issue lifecycle works with labels and comments.

---

## Phase 8 — Merge Requests
- [ ] `MergeRequest` (iid, source/target branch, source project for forks, author, assignees, reviewers, state: opened/merged/closed, draft)
- [ ] Diff + commits between source and target
- [ ] Inline diff comments (file, line, commit sha), resolvable threads
- [ ] Approvals
- [ ] Merge: merge commit / squash / fast-forward; detect conflicts
- [ ] "Delete source branch" on merge
- [ ] Update the MR automatically when the source branch receives new pushes
- [ ] Forks: fork a project, open an MR from the fork

**Done when:** you can open, review, approve and merge an MR from the UI.

---

## Phase 9 — Activity, Notifications, Webhooks
- [ ] `Event` model (push, issue opened, MR merged, ...) → user/project activity feeds
- [ ] Contribution calendar on user profile
- [ ] Todos ("To-Do List" for mentions/assignments)
- [ ] Email notifications (background jobs: Celery/RQ + Redis)
- [ ] Project webhooks (push, issue, MR events; secret token; delivery log, retry)

**Done when:** pushing to a project shows up in the activity feed and fires a webhook.

---

## Phase 10 — Frontend (React)
Build alongside the API, phase by phase:
- [ ] Vite + React + TypeScript, router, API client with JWT refresh
- [ ] Auth pages (login, register, confirm email, reset password)
- [ ] Dashboard (your projects, groups, activity)
- [ ] Project page: README, file tree, file viewer (syntax highlighting), clone URL
- [ ] Commits, branches, tags, compare views
- [ ] Issues list/detail, labels, milestones
- [ ] MR list/detail, diff viewer with inline comments
- [ ] Group pages, user profile, settings (profile, password, SSH keys, PATs)
- [ ] Admin area (or keep the Django admin)

---

## Phase 11 — Production & Extras
- [ ] Switch to Postgres (`DATABASE_URL`), Redis, background worker
- [ ] Docker Compose (web, db, redis, worker, nginx)
- [ ] Git over SSH (`authorized_keys` command → `gitlab-shell`-style dispatcher)
- [ ] Rate limiting, security headers, HTTPS
- [ ] Search (Postgres full-text first)
- [ ] Repo storage limits, LFS (stretch)
- [ ] CI/CD pipelines with a runner (stretch, large)
- [ ] OpenAPI docs (`drf-spectacular`), CI for this project
