# CLAUDE.md : Partition Map

Consignes pour une IA qui travaille sur ce dépôt.

## Le projet
Intégration Home Assistant personnalisée (domaine `partition_map`) :
- une vue façon GParted des disques et partitions de Home Assistant OS ;
- une surveillance de l'espace de stockage, avec alertes.

Elle est en **lecture seule** : aucune action sur les disques. Elle ne se connecte à aucun service tiers. Elle nécessite HAOS ou Supervised.

## Architecture
| Fichier | Rôle |
|---|---|
| `supervisor.py` | Seul point d'accès au Supervisor (`async_supervisor_get`). |
| `layout.py` | Module **pur** (aucun import HA) : construit disques → partitions depuis `/hardware/info`. |
| `coordinator.py` | Occupation toutes les 5 min, partitions toutes les 30 min, puis appel aux alertes. |
| `alerts.py` | Seuils, hystérésis, persistance (`Store`), envoi des notifications. |
| `admin_phone.py` | **Module commun SDR, copié à l'identique** (voir plus bas). |
| `config_flow.py` | Config flow (téléphone admin) et options flow (téléphone + seuils). |
| `sensor.py` / `binary_sensor.py` | Téléphone admin, occupation par stockage, partition orpheline. |
| `frontend/partition-map-panel.js` | Panneau sans build ; données via la commande WebSocket `partition_map/layout`. |

Endpoints utilisés : `/hardware/info`, `/host/info`, `/host/disks/default/usage`, `/mounts`, `/host/disks/{montage}/usage`.

## Convention « téléphone admin » (commune à toutes les intégrations SDR)
- `admin_phone.py` est copié **à l'identique** dans chaque dépôt. Ne jamais le modifier ici seul : monter `MODULE_VERSION`, puis recopier partout.
- Chaque intégration crée **sa propre** entité `sensor`, de catégorie `diagnostic` (HA refuse `config` sur un capteur), avec l'unique_id `<entry_id>_admin_notify_target`.
- État et attribut `notify_service` : le service choisi, ou `None` (état `unknown`).
- À l'installation : lecture seule des entités sœurs (`SIBLING_PLATFORMS`) pour préremplir. La valeur est **copiée** dans `entry.data[admin_notify_target]`.
- L'options flow écrit la cible dans `entry.data` (une seule source de vérité) et les seuils dans `entry.options`.
- Interdit : écrire dans une autre intégration ou modifier son entité.

## Règles
- Aucune dépendance d'exécution (`manifest.json` → `"requirements": []`).
- Ne jamais modifier le code de Sentinel ni de Spook.
- Ne jamais envoyer l'adresse e-mail du compte à un service externe.
- Textes FR et EN : `strings.json` = anglais, `translations/fr.json` et `translations/en.json` synchronisés.
- Version cohérente partout : `VERSION`, `manifest.json`, `const.py` (`VERSION`), `pyproject.toml`, README, CHANGELOG.
- Toute évolution de `entry.data` : incrémenter `MINOR_VERSION` du config flow et compléter `async_migrate_entry`.

## Vérifications avant livraison
```bash
pip install -r requirements_test.txt
pytest --cov            # couverture >= 50 % (actuellement 93 %)
ruff check custom_components/ tests/
ruff format --check custom_components/ tests/
python3 tools/check_layout.py hw.json   # sur un export réel
```
Les exports `hw*.json` ne sont pas versionnés : ils contiennent des numéros de série.
