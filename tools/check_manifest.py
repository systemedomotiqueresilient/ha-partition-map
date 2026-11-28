"""Vérifie le manifest d'une intégration SDR (modèle commun de ha-sdr).

Usage : python check_manifest.py custom_components/<domaine>/manifest.json [VERSION]
Code de sortie 0 si tout va bien, 1 sinon. Aucune dépendance.

Pourquoi : le fichier des intégrations d'Entity Inventory (0.11.0) et la
reconnaissance ouverte d'admin_phone (1.3.0) lisent ce manifest. Un champ
faux envoie une IA lire le code d'une autre intégration, ou empêche les
intégrations sœurs de se reconnaître.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

SDR_CODEOWNER = "@systemedomotiqueresilient"
REQUIRED = (
    "domain",
    "name",
    "codeowners",
    "config_flow",
    "documentation",
    "integration_type",
    "iot_class",
    "issue_tracker",
    "requirements",
    "version",
)
IOT_CLASSES = {
    "assumed_state",
    "calculated",
    "cloud_polling",
    "cloud_push",
    "local_polling",
    "local_push",
}
# Dépôt de forge : https://<hôte>/<propriétaire>/<dépôt>  (GitHub, Gitea, Forgejo…)
_REPO_RE = re.compile(r"^https://[a-z0-9.-]+(?::\d+)?/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def check(manifest: dict, version_file: str | None = None) -> list[str]:
    """Liste des problèmes (vide = conforme)."""
    problems = [f"clé manquante : {key}" for key in REQUIRED if key not in manifest]
    keys = list(manifest)
    if keys[:2] != ["domain", "name"]:
        problems.append("domain puis name doivent venir en premier (règle hassfest)")
    elif keys[2:] != sorted(keys[2:]):
        problems.append("après domain et name, les clés doivent être triées (règle hassfest)")
    if SDR_CODEOWNER not in (manifest.get("codeowners") or []):
        problems.append(f"codeowners doit contenir {SDR_CODEOWNER} (reconnaissance admin_phone)")
    docs = str(manifest.get("documentation", "")).rstrip("/")
    tracker = str(manifest.get("issue_tracker", ""))
    if not _REPO_RE.match(docs):
        problems.append(
            "documentation doit être l'adresse du dépôt : https://<hôte>/<compte>/<dépôt>"
        )
    if tracker != f"{docs}/issues":
        problems.append("issue_tracker doit valoir <documentation>/issues (même dépôt)")
    if manifest.get("iot_class") not in IOT_CLASSES:
        problems.append("iot_class inconnue")
    if manifest.get("requirements"):
        problems.append("requirements doit rester vide (pas de dépendance Python)")
    version = str(manifest.get("version", ""))
    if not _VERSION_RE.match(version):
        problems.append("version doit être de la forme x.y.z")
    if version_file is not None and version != version_file.strip():
        problems.append("version différente du fichier VERSION")
    if "<" in json.dumps(manifest):
        problems.append("valeur du modèle non remplacée (<…>)")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    manifest = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    version = Path(argv[2]).read_text(encoding="utf-8") if len(argv) > 2 else None
    problems = check(manifest, version)
    for problem in problems:
        print(f"- {problem}")
    print("Manifest conforme." if not problems else f"{len(problems)} problème(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
