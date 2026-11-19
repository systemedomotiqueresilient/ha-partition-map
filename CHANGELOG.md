# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.2.0] - 2026-11-19

### Ajouté
- **Téléphone admin**, selon la convention commune aux intégrations SDR (module `admin_phone.py`, version 1.0.0) :
  - capteur diagnostic `<entry_id>_admin_notify_target`, dont l'état et l'attribut `notify_service` contiennent le service de notification choisi ;
  - à l'installation, le champ est prérempli avec la valeur publiée par une intégration sœur (Sentinel Report, Deferred Restart, Entity Inventory, Package Keeper). Plusieurs valeurs différentes donnent une liste de choix ; sans valeur, ce sont les services `notify.mobile_app_*` qui sont proposés ;
  - la valeur est copiée dans l'entrée de config et reste valable si l'intégration sœur est supprimée.
- **Options flow** : téléphone admin, seuil d'avertissement (85 % par défaut), seuil critique (95 % par défaut) et surveillance des stockages réseau.
- **Surveillance de l'espace** de la partition data active et des stockages réseau (sauvegardes, médias) :
  - un capteur « Occupation » en % par stockage ;
  - une alerte par franchissement de seuil, réarmée 2 points sous le seuil ;
  - les niveaux d'alerte sont conservés après un redémarrage ;
  - notification persistante, plus le téléphone admin s'il est défini. Le nom d'hôte figure dans le titre, et un tag `partition_map_<stockage>` remplace la notification précédente.
- Alerte unique à l'apparition d'une partition orpheline.
- Carte « Stockages réseau » dans le panneau.
- Tests pytest (36), configuration ruff, `requirements_test.txt`, fichier `VERSION`.

### Modifié
- L'occupation est relue toutes les 5 minutes, la table des partitions toutes les 30 minutes ou à la demande avec « Actualiser ».
- L'accès au Supervisor est regroupé dans `supervisor.py`.

### Migration
- Entrées 0.1.0 (config 1.1) migrées automatiquement en 1.2 : la cible du téléphone admin est ajoutée, non définie. À renseigner via **Configurer** dans l'options flow.

## [0.1.0] - 2026-11-19

### Ajouté
- Panneau latéral façon GParted : disques, partitions à l'échelle, slots A/B, partitions orphelines, espace non alloué.
- Capteur binaire « Partition orpheline ».
- Diagnostics (numéros de série masqués).
- `tools/check_layout.py` pour analyser un export `ha hardware info --raw-json` hors Home Assistant.
