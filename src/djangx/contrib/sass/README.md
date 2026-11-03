# Sass

`djangx.contrib.sass` integrates Dart Sass with a djangX project. It compiles the
vendored Bootstrap SCSS and project Sass, serves the resulting CSS through Django's
staticfiles system, and watches project Sass files during development.

## Sources and outputs

Bootstrap and project styles have different source and output locations:

| Source                                                 | Compiled output                                                | Static path                           |
| ------------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------- |
| `djangx.contrib.sass/resources/vendor/bootstrap/scss/` | `djangx.contrib.sass/static/vendor/bootstrap/css/compiled.css` | `vendor/bootstrap/css/compiled.css`   |
| `app/<name>/static/<path>.scss` or `.sass`             | Beside the source as `<path>.css`                              | The same path with a `.css` extension |

For example, `app/blog/static/blog/css/site.scss` becomes
`app/blog/static/blog/css/site.css`, served as `static/blog/css/site.css`.
Partials whose names start with `_` are available to Sass imports but do not
produce standalone CSS files.

Project Sass discovery uses installed Django apps whose names start with `app.`.
Each app's `static/` folder is scanned recursively. `STATICFILES_DIRS` is not
scanned for Sass sources.

The compiled Bootstrap file is written into the Sass app's static directory so
Django's normal app staticfiles finder can serve and collect it. The build stamp
is stored beside it as `.settings-hash`. Project CSS is written beside its Sass
source so it is also handled by normal staticfiles finders.

## Utility modules

All Sass utilities live in `utils.py`, split by responsibility:

- `Sass` handles executable discovery and installation, command-line options, and
  generic Sass source compilation.
- `SassStatic` discovers project app static folders, maps CSS paths back to source
  files, and compiles project Sass beside each source.
- `SassBootstrap` owns Bootstrap paths, component selection, and Bootstrap entry
  source generation and compilation.
- `SassWatcher` polls project Sass folders and requests incremental builds when
  sources change.

The management commands coordinate these utilities. Template tags use
`SassStatic` for project source lookup and `SassBootstrap` for the Bootstrap URL.

## Settings

Generated project settings install `djangx.contrib.sass` and define:

```python
BOOTSTRAP_INCLUDES = ["content", "layout", "forms", "buttons"]
SASS_DART_OPTIONS = {
    "style": "compressed",
    "source_map": True,
}
SASS_EXECUTABLE = None
```

Set `BOOTSTRAP_INCLUDES` to `None` to disable Bootstrap. An empty list still
enables the Bootstrap base, helpers, and utilities. Set it to `"__all__"` to
compile the complete Bootstrap entry point, or provide a list of supported
components. Unknown component names fail the build.

`SASS_DART_OPTIONS` maps to Dart Sass command-line options. Python underscores
become option hyphens; for example, `source_map` becomes `--source-map`, and
`load_paths` accepts a list of paths. Source maps default to off unless enabled
in this setting.

`SASS_EXECUTABLE` can name a Sass executable. It can also be supplied per
command with `--sass-executable PATH`. Otherwise djangX looks in the active
virtual environment's Node environment and then on `PATH`.

## Build commands

```powershell
djx sass --build
djx sass --build --if-changed
djx sass --install
djx collectstatic
```

`djx sass --build` compiles Bootstrap when enabled and every non-partial Sass
file in discovered app static folders. Without `--if-changed`, it rebuilds all
outputs. With `--if-changed`, Bootstrap is rebuilt when its settings fingerprint
changes or its output is missing. Project Sass has a separate fingerprint based
on `SASS_DART_OPTIONS`, the executable, and djangX version; it is passed to Dart
Sass with `--update` when that fingerprint is unchanged.

Changing only `BOOTSTRAP_INCLUDES` rebuilds Bootstrap without forcing project
stylesheets to rebuild. Changing `SASS_DART_OPTIONS` or `SASS_EXECUTABLE` forces
both outputs to rebuild. The Bootstrap SCSS source directory remains on the
project Sass load path even when Bootstrap CSS is disabled, so toggling
`BOOTSTRAP_INCLUDES` does not change project Sass's import environment.

The Sass command can install `sass-embedded` automatically while building. Use
`--no-install` to prevent that, or `djx sass --install` to install it explicitly
into the current virtual environment's Node environment.

The custom `djx collectstatic` builds Sass before collecting static files. It
does not install Sass automatically; install it first, configure
`SASS_EXECUTABLE`, or pass `--install-sass`. Use `--no-sass` to skip the build.
The command excludes `.scss` and `.sass` sources and both settings stamps from
collected files. `--dry-run` skips the Sass build.

## Development flow

The Sass app's `runserver` command runs `sass --build --if-changed` before
starting Django. This compiles all discovered app Sass folders, not only the
stylesheets used by the current page. On an unchanged configuration, Dart Sass
updates stale CSS without rebuilding current outputs.

Load the template tags and refer to the CSS path relative to an app's `static/`
folder, using the `.css` extension:

```django
{% load sass %}
{% bootstrap_css %}
{% sass_css "blog/css/site.css" %}
```

`bootstrap_css` emits a link when Bootstrap is enabled and an empty string
otherwise. `sass_css` is a link-tag wrapper around `sass_url`.

With `DEBUG=True`, the first `sass_url`/`sass_css` use for a source checks its
adjacent CSS. If the CSS is missing or older than the source, it triggers an
incremental Sass build. It then registers that source folder with
`SassWatcher`. A single daemon thread polls watched folders every half second,
including partials; changes trigger `sass --build --if-changed`. The runserver
build normally makes the first-use freshness check a no-op, while the tag is
what registers the folder for subsequent edits.

When `django-browser-reload` is installed in development, the Sass app replaces
its file-change receiver so `.scss` and `.sass` source events do not trigger a
browser reload before compilation. Other changes, including the generated CSS,
are forwarded to `django-browser-reload` normally.

With `DEBUG=False`, template tags only produce static URLs. Production CSS must
be built before running `collectstatic`.
