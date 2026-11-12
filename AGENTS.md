# Repository guide

## Project and scope

This repository generates the Spanish-language Sin Dioses website with Nikola. It contains editorial content, static assets, local Nikola plugins, and several bundled themes. There is no application server or root JavaScript build pipeline.

- Python requirement: `>=3.13`.
- Dependencies and environment: `pyproject.toml` and `uv.lock`, managed with `uv`.
- Direct project dependencies: `nikola[extras]>=8.3.3` and `ghp-import>=2.1.0`.
- Site language: `es`. Only Spanish is enabled in `TRANSLATIONS`, even though some sources have language suffixes such as `.en.rst`.
- Time zone: `America/Buenos_Aires`.
- Run site commands from the repository root, where `conf.py` lives.

## Source map

| Path | Purpose |
| --- | --- |
| `conf.py` | Nikola configuration, content discovery, navigation, redirects, theme, feeds, galleries, and deployment settings. |
| `conf.json` | Site author, title, email, and URL. `conf.py` reads this sibling file as UTF-8 using `Path(__file__)`. |
| `posts/` | Articles organized into section directories, including the creationist-claims index under `cienciaorigenes/indiceac/`. |
| `stories/` | Standalone pages and section indexes. `principal.rst` is the main content page. |
| `includes/` | Shared reStructuredText fragments, section footers, credits, and translation notices. |
| `files/` | Files copied to the output root, including the entrance page `index.html`, `CNAME`, error pages, images, and downloads. |
| `images/` | Nikola-managed images mapped to the output root. Also contains the diagram source `DiagramaDiscusion.puml`. |
| `galleries/cerdoateo/` | Gallery sources, descriptions, and `metadata.yml`; published under `humor/cerdoateo/`. |
| `shortcodes/` | Mako shortcodes `band.tmpl` and `biblia.tmpl`. |
| `themes/sindioses/` | Active site theme and site-specific template/CSS overrides. |
| `themes/bootstrap3/` | Local parent theme for `sindioses`, with shared layout, assets, and bundles. |
| `themes/sindioses0/`, `themes/octopress/`, `themes/planetoid/`, `themes/reveal/` | Other bundled themes. They are not selected by `THEME`. Octopress uses Jinja; the active theme uses Mako. Reveal includes its own legacy JavaScript project and tests. |
| `plugins/` | Local Nikola compiler extensions, category navigation, and a metadata migration command. |
| `_plugins/tags/` | Legacy tag-management plugin kept separately from `plugins/`. |
| `checkoutput.py` | Missing-local-image report for generated HTML. |
| `gen_sitemap.py` | Legacy sitemap generator that overwrites `output/sitemap.xml`. |
| `justfile` | Build and GitHub deployment recipes. |
| `openspec/` | OpenSpec configuration, main specifications, and changes. Current configuration uses `schema: spec-driven`. |

`output/`, `cache/`, `.doit.db*`, `__pycache__/`, and `*.bak` are ignored build/cache artifacts. Edit their sources rather than generated HTML or cached fragments. Preserve unrelated working-tree changes and do not add local environments, IDE state, or caches to a change.

## Commands and validation

Launch `nu.exe` directly for shell commands, using `nu -c "<Nushell command>"`.
Nushell is on PATH. Replace the execution shell itself: do not launch Nushell
through PowerShell or `cmd.exe`, and do not send Nushell syntax to either shell.
Do not substitute PyCharm terminal MCP calls for the standard command runner.
If the available runner cannot launch Nushell directly, report that limitation
instead of silently using a wrapper or claiming this preference was followed.

```powershell
# Install the versions recorded in the lockfile
uv sync --locked

# Build the website
uv run nikola build

# Equivalent build recipe; additional parameters pass through to Nikola
just gen

# Preview the generated site
uv run nikola serve

# Report missing local images after building
uv run --script checkoutput.py
```

The `justfile` selects `pwsh -nologo -c` as its Windows shell. `just gen` runs `uv run nikola build`; it does not run the image checker. Use `uv` for dependency changes and update `uv.lock` together with `pyproject.toml` when dependencies change.

There is no repository-wide application test suite or CI workflow checked in. The `Tests` fields in some plugin descriptors refer to tests that are not present here. Reveal's bundled QUnit/Grunt tests cover that library, not the website.

For content, configuration, plugin, or template changes, build the site and inspect the affected generated pages. For shared theme changes, also check `principal.html`, a section index, a normal article, and the gallery at desktop and narrow widths. Check image paths after asset changes. A successful build alone does not establish that the rendered HTML, links, or external integrations work.

Ruff configuration in `pyproject.toml` sets a 160-character line length and extends lint selection with import sorting rule `I`. Ruff is not declared as a project dependency. If available in the configured development environment, run it on changed Python files without reformatting unrelated legacy code.

## Content and URL conventions

- Keep editorial content in Spanish unless the task concerns an existing translation. Preserve UTF-8 text, accents, attribution, source links, and publication metadata.
- Both `.rst` and `.txt` in `posts/` and `stories/` use the reStructuredText compiler. The configured default template for both is `postsd.tmpl`. Other compiler extensions listed in `COMPILERS` do not by themselves add new content-discovery patterns.
- Content generally uses inline Nikola metadata, with `.. title:`, `.. slug:`, `.. date:`, `.. tags:`, `.. category:`, `.. author:`, and `.. description:` before a blank line. Follow a neighboring source for the relevant section. Some files also start with editor modelines.
- A `.. template:` field overrides the default. Section indexes commonly select `story.tmpl`, and `stories/principal.rst` selects `indice.tmpl`.
- `.. type:` affects article CSS classes and the images supplied by `GLOBAL_CONTEXT['dictimg']`. `.. nocomments:` suppresses comments in the site templates. Preserve these fields when editing content.
- Category names drive `.. post-list::` filters and category navigation. Section indexes select custom `post_list_*.tmpl` templates. Preserve category spelling and case, and check those lists when changing classification.
- `CATEGORY_DESTPATH_AS_DEFAULT` derives categories from destination paths when needed. `CATEGORY_DESTPATH_NAMES` supplies Spanish display names; hierarchy support is disabled and only the first destination directory is used for defaults.
- Use existing Nikola `:doc:` links and shared `.. include:: includes/...` fragments where appropriate. Source filenames, slugs, and references such as uppercase `CA100` are linked throughout the content.
- Preserve published paths and filename case. `URL_TYPE = 'rel_path'`, `PRETTY_URLS = False`, and `STRIP_INDEXES = True`. The site combines `.html` article URLs with directory index links.
- `files/index.html` is the static entrance page linking to `principal.html`. Do not replace it with a generated blog index. Automatic indexes are disabled, `INDEX_PATH` is `ignorar`, and the archive plugin is disabled.
- Review `REDIRECTIONS` in `conf.py` when moving published pages. Keep old inbound links working.
- `USE_TAG_METADATA` and `WARN_ABOUT_TAG_METADATA` are enabled for legacy metadata compatibility. Do not migrate the whole content collection as part of an unrelated edit.

## Theme and static assets

The active inheritance starts with `themes/sindioses/parent`, which names `bootstrap3`. Templates missing from these directories can come from Nikola's installed base themes. Preserve template inheritance, namespace imports, and context-variable contracts when making overrides.

- `postsd.tmpl` renders normal content, sharing, type-specific images, tags, category previous/next navigation, comments, and math support.
- `story.tmpl` supplies standalone-page rendering; `indice.tmpl` supplies the main page; `post_list_*.tmpl` controls the different section lists; `gallery.tmpl` supplies gallery rendering and JavaScript setup.
- `GLOBAL_CONTEXT` in `conf.py` supplies `dictimg` and `addtoany` to templates. The helper templates also supply Open Graph and Twitter metadata.
- Prefer site-specific changes under `themes/sindioses/`. Edit `themes/bootstrap3/` when the shared parent behavior itself must change.
- `themes/sindioses/assets/css/custom.css` contains active site overrides, including article styling and responsive main-page columns. The directory also retains `sindioses.css` and `sindiosestit.css`.
- The active parent bundle definitions are in `themes/bootstrap3/bundles`. `themes/sindioses/bundles.old` and `bundles.new` are saved variants, not a file named `bundles`; do not assume editing them changes the build.
- `files/` and `images/` both map assets into the output root. Check for output-path collisions and preserve public asset paths. Nikola uses a 400-pixel image thumbnail size; the gallery uses 180-pixel thumbnails and a 1280-pixel maximum image size.
- `band.tmpl` renders a flag from `band/<argument>.svg` with a caller-provided width. `biblia.tmpl` creates a BibleGateway link or iframe, with an optional `alto` height.
- The themes include vendored Bootstrap, jQuery, Reveal, HTML5 shims, and other legacy scripts. Keep changes scoped to the requested behavior; preserve bundled licenses and copyright notices.

The site integrates Disqus, AddToAny, search, StatCounter, and externally loaded scripts. A local build does not validate these services. The configured content license permits educational/scientific reproduction with site and author attribution and prohibits commercial reproduction. Preserve those credits and notices.

## Plugins and maintenance scripts

| Component | Behavior and constraints |
| --- | --- |
| `plugins/category_prevnext/` | A `SignalHandler` connects to `taxonomies_classified` and rewrites `prev_post`/`next_post` within each category. Check category boundaries when changing navigation. |
| `plugins/book_figure/` | Registers `.. book_figure::` and renders raw HTML for book covers, titles, authors, ISBN/ASIN data, and reviews. Its output classes are styled in the custom CSS. |
| `plugins/sphinx_roles/` | Adds Sphinx-like roles, directives, labeled math, glossary references, `EXTLINKS`, and a `today` substitution transform. Several references work only within the same document. This is a Nikola/docutils extension, not a Sphinx documentation build. |
| `plugins/upgrade_metadata_v8/` | A command that rewrites source metadata, converting legacy draft/private/math tags and section fields. It prompts before writing unless `--yes` is supplied. Treat it as a migration, not a validation step. |
| `_plugins/tags/` | Supports listing, searching, sorting, merging, adding, removing, and suggesting tags. Mutating operations rewrite source headers and support `--dry-run`. Auto-tagging optionally uses NLTK and its data. This legacy directory is not added through `EXTRA_PLUGINS_DIRS` in `conf.py`; verify discovery and compatibility before relying on it. |
| `gen_sitemap.py` | Walks generated HTML and writes sitemap entries using `lxml` and `arrow`. It hardcodes `http://www.sindioses.org`, uses modification times, and has Windows-specific path exclusions. Review before using it instead of Nikola's sitemap generation. |
| `posts/cienciaorigenes/indiceac/pendientes.py` | Audits missing claim references using source files, generated docutils system messages, `asignados.yaml`, and `pendientes.db`. Run from its own directory. It opens SQLite at import time and updates the database during the normal report. Its `load_info` alternative fetches TalkOrigins pages and stores them. Legacy imports include `clize`, `colorama`, `requests`, YAML, BeautifulSoup, and lxml; they are not all direct project dependencies. |
| `posts/cienciaorigenes/indiceac/vertags.py` | Recursively rewrites `.rst` headers below the current directory to add missing `type: afirmacrea` and descriptions. It assumes a particular title/header format. Run only for an intended metadata edit in the claims directory. |
| `*.btm` | Legacy JP Software/TCC scripts, not PowerShell or ordinary Windows batch files. Includes FTP deployment, gallery metadata generation, SQLite extraction, and browser helpers. Some depend on local commands/aliases such as `ba:GetOpt.btm` and `k`. |

Keep plugin `.plugin` descriptors with their modules. Do not assume every legacy utility's dependencies or external tools are installed by the main project's `uv sync`.

### Image checker details

`checkoutput.py` has PEP 723 script metadata for Python `>=3.13` and dependencies `beautifulsoup4`, `lxml`, and `rich`. Use `uv run --script checkoutput.py` so its script dependencies are resolved.

It scans `output/**/*.html` as UTF-8, parses with BeautifulSoup's lxml parser, ignores image sources starting with `http`, URL-decodes the source, removes its query string, and resolves it relative to the generated page's directory. It prints warnings and a sorted Rich table of missing images.

Account for these limits when interpreting results or changing the checker:

- It deduplicates raw `src` strings globally in the module-level `imglocales` set, so the same relative source used from different page directories is checked only once.
- Root-relative sources, protocol-relative URLs, data URLs, fragments, and `srcset` do not receive special handling.
- It does not check ordinary hyperlinks or fetch external images.
- A missing or empty `output/` produces an empty report. Missing images do not produce an explicit failing exit status, so this is currently a manual report rather than a CI gate.

## Deployment

`just deploy <message>` runs `uv run nikola github_deploy -m "<message>"`. Configuration names `src` as the source branch, `master` as the deployment branch, and `origin` as the remote. `GITHUB_COMMIT_SOURCE = True` means deployment can also commit source changes. `files/CNAME` contains `sindioses.org`.

Run deployment only when publication is requested. Review the working tree before it can be committed or pushed. `deploy.btm` is a separate legacy FTP upload using a local `sindioses` connection profile; it is not required for a local build or validation.

## OpenSpec

OpenSpec workflows are available through repository skills under `.agents/skills/` and matching OpenCode resources under `.opencode/`. For an OpenSpec task, follow the relevant skill and keep proposal/design/tasks, delta specifications, and implementation consistent. `openspec/config.yaml` currently adds no project-specific artifact rules or context. Ordinary maintenance does not require inventing an OpenSpec change unless requested.
