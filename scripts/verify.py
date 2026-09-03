#!/usr/bin/env python3
# verify.py — Maschinen-Gate fuer usely.yg-media.de (abgeleitet vom YG-MEDIA-Gate, Pattern P-7)
# stdlib-only. Exit 0 = gruen, Exit 1 = rot. Vor JEDEM Commit gruen erforderlich.
# Prueft: DNA-Marker, Em-Dashes, Canonical, Title-/Description-Laenge, JSON-LD-Validitaet,
# Schema-Wahrheit (Preise sichtbar), interne Links + Assets, Sitemap, CNAME, Consent-Gate.

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://usely.yg-media.de"
PAGES = ["index.html"]

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def visible_text(html):
    """Entfernt title, meta, script, style und Kommentare — der Rest gilt als sichtbarer Text."""
    html = re.sub(r"<title>.*?</title>", "", html, flags=re.S | re.I)
    html = re.sub(r"<meta\b[^>]*>", "", html, flags=re.I)
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return html


def check_invariants():
    for f in ["CNAME", "robots.txt", "sitemap.xml", "index.html"]:
        if not os.path.exists(os.path.join(ROOT, f)):
            err(f"Invariante: {f} fehlt im Repo")
    if os.path.exists(os.path.join(ROOT, "CNAME")):
        cname = read("CNAME").strip()
        if cname != "usely.yg-media.de":
            err(f"CNAME ist '{cname}', erwartet usely.yg-media.de")


def check_page(path):
    html = read(path)

    # Sprache
    m = re.search(r"<html[^>]*\blang=\"([a-zA-Z-]+)\"", html)
    if not m or m.group(1).lower().split("-")[0] != "de":
        err(f"{path}: lang-Attribut fehlt oder nicht de")

    # DNA-Marker (gleiche Handschrift wie yg-media.de)
    for marker, name in [("<nav", "Navbar"), ("<footer", "Footer"), ("<canvas", "Canvas-Hintergrund"),
                         ("orb-wrap", "Orbs"), ("grid-overlay", "Grid-Overlay"), ("cookieBanner", "Cookie-Banner")]:
        if marker not in html:
            err(f"{path}: {name} fehlt (DNA)")

    # Consent vor Tracking
    if "usely_cookie_consent" not in html:
        err(f"{path}: Consent-Gate (usely_cookie_consent) fehlt")
    if "googletagmanager.com/gtag/js" in html and "loadAnalytics" not in html:
        err(f"{path}: GA-Snippet ohne Consent-Funktion")
    if not re.search(r"const GA_ID = '(G-[A-Z0-9]+)?'", html):
        err(f"{path}: GA_ID-Konstante fehlt oder hat unerwartetes Format")

    # Em-Dash (§A2 der YG-Constitution, hier uebernommen)
    for i, line in enumerate(visible_text(html).splitlines(), 1):
        if "—" in line:
            err(f"{path}: Em-Dash im sichtbaren Text (Zeile ~{i}): {line.strip()[:90]}")

    # Title + Description
    t = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    if not t:
        err(f"{path}: kein <title>")
    elif len(t.group(1)) > 65:
        warn(f"{path}: Title {len(t.group(1))} Zeichen (>65, wird in der Suche abgeschnitten)")
    d = re.search(r'<meta name="description" content="([^"]*)"', html)
    if not d:
        err(f"{path}: keine Meta-Description")
    elif not (120 <= len(d.group(1)) <= 175):
        warn(f"{path}: Description {len(d.group(1))} Zeichen (Zielbereich 120-175)")

    # Canonical
    canon = re.findall(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"', html)
    if len(canon) != 1:
        err(f"{path}: {len(canon)} Canonicals, erwartet genau 1")
    elif canon[0] != SITE + "/":
        err(f"{path}: Canonical zeigt auf {canon[0]}, erwartet {SITE}/")

    # noindex darf NICHT drin sein
    if re.search(r"<meta[^>]*noindex", html):
        err(f"{path}: indexierbare Seite traegt noindex")

    # JSON-LD valide + Schema = sichtbare Wahrheit
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S)
    if not blocks:
        err(f"{path}: kein JSON-LD")
    kinds = []
    for block in blocks:
        try:
            data = json.loads(block)
            kinds.append(data.get("@type"))
        except Exception as e:
            err(f"{path}: ungueltiges JSON-LD ({e})")
            continue
        if data.get("@type") == "SoftwareApplication":
            for offer in data.get("offers", []):
                preis = offer.get("price", "")
                if preis not in ("0",) and preis.replace(".", ",") not in visible_text(html):
                    err(f"{path}: Schema-Preis {preis} steht nicht sichtbar auf der Seite (Schema = sichtbare Wahrheit)")
        if data.get("@type") == "FAQPage":
            for q in data.get("mainEntity", []):
                frage = q.get("name", "")
                if frage and frage not in html:
                    err(f"{path}: FAQ-Schema-Frage nicht sichtbar auf der Seite: {frage[:60]}")
    for want in ("SoftwareApplication", "FAQPage"):
        if want not in kinds:
            err(f"{path}: JSON-LD {want} fehlt")

    # Interne Links und Assets
    for href in re.findall(r'href="(/[^"]*)"', html):
        f = href.lstrip("/").split("#")[0].split("?")[0]
        if f and not os.path.exists(os.path.join(ROOT, f)):
            err(f"{path}: toter interner Link {href}")
    for src in re.findall(r'src="(/[^"]+)"', html):
        f = src.lstrip("/").split("?")[0]
        if not os.path.exists(os.path.join(ROOT, f)):
            err(f"{path}: totes Asset {src}")

    # Anker muessen existieren
    for anchor in set(re.findall(r'href="#([a-z-]+)"', html)):
        if f'id="{anchor}"' not in html:
            err(f"{path}: Anker #{anchor} hat kein Ziel")

    # App-Store-Link + Web-App-Link vorhanden
    if "apps.apple.com/de/app/usely/id6783429050" not in html:
        err(f"{path}: App-Store-Link fehlt")


def check_sitemap():
    try:
        tree = ET.parse(os.path.join(ROOT, "sitemap.xml"))
    except Exception as e:
        err(f"sitemap.xml: kein valides XML ({e})")
        return
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [u.text.strip() for u in tree.findall(".//sm:loc", ns)]
    if urls != [SITE + "/"]:
        err(f"sitemap.xml: erwartet genau [{SITE}/], gefunden {urls}")


def main():
    check_invariants()
    for p in PAGES:
        if os.path.exists(os.path.join(ROOT, p)):
            check_page(p)
    check_sitemap()

    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        for e in errors:
            print(f"FAIL  {e}")
        print(f"\nverify.py ROT — {len(errors)} Fehler, {len(warnings)} Warnungen. NICHT committen.")
        sys.exit(1)
    print(f"verify.py GRUEN — {len(PAGES)} Seite(n) geprueft, 0 Fehler, {len(warnings)} Warnungen.")
    sys.exit(0)


if __name__ == "__main__":
    main()
