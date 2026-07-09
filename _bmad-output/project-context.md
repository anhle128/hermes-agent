---
project_name: 'hermes-agent'
user_name: 'kevin'
date: '2026-07-09'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - quality_rules
  - workflow_rules
  - anti_patterns
existing_patterns_found: 16
status: 'complete'
rule_count: 70
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Python runtime is `>=3.11,<3.14`. The `<3.14` cap is load-bearing because current Rust-backed transitives may fall back to failing source builds on Python 3.14.
- Package version is `hermes-agent 0.18.0`; architecture handoff references workspace version `0.17.0`, so prefer package metadata for current implementation work.
- Core Python dependencies are intentionally tight: `openai==2.24.0`, `pydantic==2.13.4`, `pytest==9.0.2`, `ruff==0.15.10`, `rich==14.3.3`, `prompt_toolkit==3.0.52`, `psutil==7.2.2`, `websockets==15.0.1`, `Pillow==12.2.0`.
- Web/server surfaces use FastAPI `>=0.104.0,<1`, Uvicorn `>=0.24.0,<1`, and Starlette is pinned in server-related extras where security requires it.
- Root Node workspace requires Node `>=20.0.0`; desktop requires `^20.19.0 || >=22.12.0`.
- TypeScript UI work uses React 19 and TypeScript 6 across multiple surfaces: Ink TUI, dashboard web, Electron desktop, shared package, and Tauri bootstrap installer.
- TUI stack: Ink `^6.8.0`, React `^19.2.4`, nanostores `^1.2.0`, Vitest `^4.1.3`, TypeScript `^6.0.3`.
- Dashboard web stack: Vite `^8.0.16`, React `^19.2.4`, React Router `^7.17.0`, Tailwind `^4.2.1`, xterm `^6.0.0`, `@hermes/shared` via local workspace.
- Desktop stack: Electron `40.10.2`, React `^19.2.5`, Vite `^8.0.10`, TypeScript `^6.0.3`, nanostores `^1.3.0`, assistant-ui, xterm, and `@hermes/shared`.
- Bootstrap installer stack: Tauri 2, Vite 8, React 19, TypeScript 6.
- Architecture handoff for Workflow Commander work says no new runtime infrastructure for v1; use existing local Hermes process, existing SQLite-backed substrate, ports/adapters, signed typed events, outbox/reconciliation, and schema-versioned JSON contracts.

## Critical Implementation Rules

### Language-Specific Rules

- Python code must keep file I/O encoding-explicit in core paths. Ruff only enforces `PLW1514`, because locale-default text I/O corrupts non-ASCII content on Windows.
- Use `get_hermes_home()` / related helpers from `hermes_constants.py` for Hermes paths. Do not hand-roll `~/.hermes`, and do not mutate `os.environ` for per-task home scoping; use the context-local override helpers.
- Subprocess spawners must propagate `HERMES_HOME` explicitly when profile isolation matters. Falling back to the default profile is diagnosable but still dangerous.
- For sync code scheduling coroutines onto another event loop, use `agent.async_utils.safe_schedule_threadsafe()` or match its coroutine-closing behavior; failed scheduling must not leak never-awaited coroutine objects.
- New Python dependencies should be exact-pinned when they ship in core. Provider/platform/backend-specific packages belong in extras and lazy-deps allowlists, not base dependencies.
- TypeScript surfaces are strict: `strict: true`, ES2023 targets, `noEmit`, React JSX, and source-only local workspace imports such as `@hermes/shared`.
- Desktop and TUI ESLint require `import type` for type-only imports, sorted imports/exports/named imports, sorted JSX props, curly braces, and no unused imports.
- Prefer interfaces for public props and shared object shapes. Use type aliases only when they express unions, primitives, or mapped/utility compositions better than an interface.
- For UI event handlers with side effects, use explicit void intent, e.g. `onClick={() => void save()}` and `onState={st => void setGatewayState(st)}`.
- Keep table-driven mappings for ids, routes, slash commands, and view dispatch. Do not add parallel lists or switch ladders when an existing registry/table is the source of truth.

### Framework-Specific Rules

- The agent loop is synchronous in `run_agent.py`; preserve OpenAI-style role alternation and byte-stable system prompts during a conversation. Skill commands inject as user messages, not system prompt mutations.
- Tool files register with `tools.registry` at import time, but a tool is not exposed until it is included in a toolset. Built-in tools require both `tools/<name>.py` and `toolsets.py` wiring.
- Tool handlers must return JSON strings. Use `check_fn` for service-gated availability rather than exposing tools unconditionally.
- Slash commands live in `hermes_cli/commands.py` as the central registry. Add aliases only on `CommandDef`; downstream CLI, gateway, help, Telegram, Slack, and autocomplete surfaces derive from that table.
- The TUI is Ink over stdio JSON-RPC to `tui_gateway`; TypeScript owns rendering, Python owns sessions, tools, model calls, and slash command logic.
- The dashboard `/chat` embeds the real `hermes --tui` through a PTY and xterm. Do not rebuild the primary transcript, composer, or slash behavior in dashboard React; extend Ink so dashboard inherits it.
- Dashboard React around the PTY is allowed only as supporting UI: sidebars, inspectors, status panels, summaries. Failures there must not break the terminal pane.
- The Electron desktop app is a separate chat surface. It does not embed `hermes --tui`; it uses its own React/assistant-ui transcript and talks to a `tui_gateway` backend through JSON-RPC.
- Desktop and dashboard share transport helpers through `@hermes/shared`, but desktop must not depend on dashboard frontend code. Desktop launches `hermes serve`, with legacy fallback to `dashboard --no-open` only for older runtimes.
- Desktop slash palette curation must hide noisy built-ins, not user extensions. Keep skill commands and `quick_commands` flowing through both suggestion and execution paths.
- Desktop slash dispatch should use the existing `slash.exec` then `command.dispatch` fallback path unless the command is explicitly owned by desktop UI.
- For React state shared across distant UI, prefer small nanostores near the owning feature. Route roots should compose shell and routes, not become controllers.

### Testing Rules

- Prefer `scripts/run_tests.sh` for Python tests. It runs per-file subprocess isolation, deterministic env (`TZ=UTC`, `LANG=C.UTF-8`, `PYTHONHASHSEED=0`), and the project venv.
- Pytest defaults to `tests` and excludes `integration` via `addopts = "-m 'not integration'"`; mark slow/external-service tests with `@pytest.mark.integration`.
- Tests that touch config, sessions, profiles, skills, plugins, gateways, file/network I/O, or security boundaries should use real imports and a temp `HERMES_HOME`, not only mocks.
- Never hardcode `~/.hermes` in tests. If a test patches `Path.home()`, also set `HERMES_HOME` to the intended temp profile/home.
- Write behavior-contract tests over snapshot/change-detector tests. Assert invariants and relationships, not mutable catalog counts, model-list contents, config-version literals, or current enumeration sizes.
- For dependency/security metadata, test the invariant that surfaces stay in sync, e.g. pyproject pins matching lazy-deps pins, rather than duplicating unrelated package lists.
- For slash command and UI curation behavior, test both discovery and execution paths. Desktop slash tests must keep extension commands visible while noisy built-ins stay hidden.
- For TypeScript surfaces, use the package-local commands: TUI `npm test`, `npm run typecheck`, `npm run lint`; web `npm test`, `npm run typecheck`, `npm run lint`; desktop tests run from the root workspace dependency install where required.
- Add focused regression tests at the boundary where the bug manifests. If a change affects multiple sibling paths, cover the shared invariant or every affected path.
- Do not rely on module-level state leaking between tests; the runner intentionally isolates Python files, and test setup should be explicit.

### Code Quality & Style Rules

- Non-secret behavior settings belong in `config.yaml`, not `.env`. `.env` is for credentials only; dashboard env writers also denylist loader/runtime variables such as `PATH`, `PYTHONPATH`, `NODE_OPTIONS`, `HERMES_HOME`, and editor/shell variables.
- When adding config keys, update `DEFAULT_CONFIG` in `hermes_cli/config.py`. Bump `_config_version` only for migrations or shape changes, not simple new keys.
- Know the config loader path: CLI uses `load_cli_config()` in `cli.py`; setup/tools/subcommands use `load_config()`; gateway runtime may read YAML through `gateway/run.py` and `gateway/config.py`.
- Persistent settings should use existing config helpers such as `save_config_value()` and preserve profile-aware paths.
- Keep plugins out of core files. If a plugin needs more surface, add a generic hook/context method instead of hardcoding plugin-specific branches into `run_agent.py`, `cli.py`, `gateway/run.py`, or `hermes_cli/main.py`.
- New third-party product integrations and new memory providers should be standalone plugins, not new in-tree directories under `plugins/`.
- Keep heavy or niche skills in `optional-skills/`; built-in `skills/` should stay broadly useful and lightweight.
- For package data that must survive wheel/sdist installs, update setuptools metadata in `pyproject.toml`; do not assume bare directories like `locales/`, `optional-mcps/`, or plugin manifests are automatically included.
- In TypeScript, `src/app` owns routes/pages/page-specific components, `src/store` owns shared atoms, and `src/lib` owns shared pure helpers. Keep route roots thin.
- Hooks should own one narrow job. Prefer colocated action modules over hidden god hooks, and do not pass state through several components when a leaf can subscribe to the atom.
- Preserve lint expectations: explicit curly braces, sorted imports/exports/JSX props where configured, no unused imports, and `import type` for type-only imports.
- Add comments only for non-obvious invariants, lifecycle constraints, or security/compatibility rationale. Avoid narrating obvious assignments or control flow.

### Development Workflow Rules

- Before building a feature or fix, search existing code, open issues, merged PRs, and open PRs. Many requested capabilities already exist or have in-flight work.
- For bug fixes, reproduce the symptom on current code and identify the exact line/path where it manifests. Do not fix a plausible premise without tracing runtime behavior.
- When a missing link or restriction looks like a gap, check intent first with source history such as `git log -p -S "<symbol>"`. Some omissions are load-bearing.
- Use the Footprint Ladder for new capability: extend existing code, then CLI command + skill, then service-gated tool, then plugin, then MCP catalog, then core tool only as last resort.
- Dependency changes must preserve the security model: core deps exact-pinned where policy requires, backend-specific deps in extras/lazy-deps, and lockfile regenerated with `uv lock`.
- Run focused validation for the changed surface: Python via `scripts/run_tests.sh ...`; TUI/web/desktop via their local `npm run typecheck`, `npm run lint`, and `npm test` commands as applicable.
- Workflow Commander implementation is not ready until shared contract fixtures and Archon producer-side contracts exist locally or are regenerated into this handoff. Do not move blocked stories to implementation-ready without those artifacts.
- For Workflow Commander stories, preserve the no-new-frontend scope unless product scope changes. Existing dashboard/Kanban/task surfaces are reused.
- Split sprint stories before commitment when they cannot be implemented, tested, linted, and validated in one implementation cycle.
- Preserve contributor credit when salvaging external work. Prefer cherry-pick/rebase-merge style salvage over reimplementation when the contribution is usable.

### Critical Don't-Miss Rules

- Do not mutate past conversation context, swap toolsets, reload memories, or rebuild system prompts mid-conversation. Only context compression may alter context.
- Do not inject synthetic user messages mid-loop or produce same-role adjacent messages. Gateway/cron/background deliveries must preserve OpenAI role alternation.
- Do not hardcode `~/.hermes`, `Path.home() / ".hermes"`, or user-visible `~/.hermes` strings for state paths. Use `get_hermes_home()` and `display_hermes_home()`.
- Do not add non-secret `HERMES_*` env vars as user-facing configuration. Use `config.yaml` and bridge internally only when compatibility requires it.
- Do not mention tools from other toolsets inside static tool schema descriptions. Availability varies; cross-tool hints must be added dynamically when both tools are present.
- Do not add `offset`/`limit` pagination to instructional readers for skills, prompts, playbooks, or rules. Agents must read those files fully.
- Do not use POSIX-only process assumptions casually. Avoid `os.kill(pid, 0)`, unguarded `os.setsid`, `os.killpg`, `os.fork`, POSIX-only signals, hardcoded `/tmp`, or shell utilities without Windows fallbacks.
- Do not use ANSI erase-to-EOL `\033[K` in spinner/display code under prompt_toolkit; use space-padding to clear lines.
- Do not add new `simple_term_menu` call sites; use the curses UI pattern for new interactive menus.
- Gateway commands that must work while an agent is blocked, such as approval/control commands, must bypass both the base adapter pending-message guard and the gateway runner interrupt guard.
- Do not wire unused/dead modules into live paths without E2E validation using actual imports and a temp `HERMES_HOME`.
- Do not treat `sprint-status.yaml`, GitHub PR state, or provider UI state as Hermes runtime queue truth. Hermes owns Project Work Items, Phase Tasks, gates, timeline, and reconciliation.
- Do not auto-approve HILT gates or mark stories complete when evidence conflicts. A merged PR is not the same as done-verification approval.
- Workflow provider events are accelerators, not the sole source of truth. Reconciliation must handle loss, duplicates, gateway downtime, command failure, and manual PR merges.
- Redact secrets, raw event signatures, and unredacted command output from command logs, event logs, diagnostics, timeline views, and HILT prompts.
- For Workflow Commander event ingress, reject wrong profile, wrong binding, wrong codebase, stale timestamp, duplicate event id, invalid signature, unsupported provider, and schema failure before mutation.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing code in this project.
- Follow all rules exactly as documented.
- When in doubt, prefer the more restrictive option.
- Update this file if new non-obvious implementation patterns emerge.

**For Humans:**

- Keep this file lean and focused on agent needs.
- Update it when the technology stack or project conventions change.
- Review periodically for outdated rules.
- Remove rules that become obvious or obsolete over time.

Last Updated: 2026-07-09
