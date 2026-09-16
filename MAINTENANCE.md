# ShadowBlue profile maintenance

## Local preview

From the repository root, start any static HTTP server. Python is sufficient:

```powershell
python -m http.server 8080
```

Then open `http://127.0.0.1:8080/docs/`. Do not open `docs/index.html` directly because browser module imports require HTTP.

## Validation

```powershell
npm run validate
python scripts/validate.py
```

The first command checks required files, local README paths, token/path leaks, and JavaScript syntax. The second parses every SVG as XML and performs structural workflow checks.

## Publishing

The repository must remain public and named exactly `Deadking1i1`. GitHub automatically renders its root `README.md` on the `Deadking1i1` profile.

The Pages workflow deploys the interactive experience from `docs/` with shared assets copied into the published artifact. In **Settings → Pages**, select **GitHub Actions** as the source if GitHub does not do so automatically.

## External services

- Three.js is pinned to `0.186.0` from jsDelivr in `docs/index.html`.
- GitHub statistics and the contribution calendar are generated into `generated/` from GitHub's own REST and GraphQL APIs. The scheduled workflow uses the repository-scoped `GITHUB_TOKEN`; no personal token or third-party statistics service is required.
- The generated metric files are committed by `github-actions[bot]` only when their content changes.
- No custom secret is required by any workflow.

## Inputs still needed

Add only verified URLs for LinkedIn, YouTube, X/Twitter, and any separate portfolio. Repository links for JVR Workshop, H&D Part Sales, EON, and NST should be added only once those repositories are public and their exact URLs are known.

## GitHub rendering limitations

GitHub does not run JavaScript in READMEs, so the profile uses self-contained animated SVGs. Browser support and GitHub's image proxy can affect SVG animation; reduced-motion rules are embedded in both assets, and the artwork remains meaningful when animation is disabled. The full WebGL interaction is therefore deployed as a separate GitHub Pages site.
