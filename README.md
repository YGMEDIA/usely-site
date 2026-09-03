# usely.yg-media.de

Produkt-Website für USELY (Rechnungs App für Selbstständige), ein Produkt von YG MEDIA.

- Reines HTML/CSS/JS, eine Seite (`index.html`), Assets unter `assets/`.
- Design: YG-Handschrift (Canvas-Partikel, Orbs, Grid, Grain, Glass-Cards) in USELY-Farben
  aus `design-tokens/tokens.json` des USELY-Repos (Teal #1DDEB4, Hintergrund #18181E).
- Deploy: GitHub Pages via Actions (`.github/workflows/deploy.yml`), Domain per `CNAME`.
- Gate: `python3 scripts/verify.py` muss vor jedem Commit grün sein.
- Lokal ansehen: `python3 -m http.server 8766` im Repo-Root.

Spec, Keyword-Daten und Protokoll liegen im YG-MEDIA-Repo (`brain/06-specs/SPEC-usely-onepager.md`,
`brain/03-research/raw/keywords/`).
