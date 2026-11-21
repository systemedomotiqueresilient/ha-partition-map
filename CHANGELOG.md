# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.4.1] - 2026-11-21

### Modifié
- Module commun `admin_phone.py` passé en **MODULE_VERSION 1.2.0**, copié tel quel depuis ha-sdr (commit 77a8992, SHA-256 `1d720150…545b`, vérifié par un test). Outdoor Brief fait désormais partie des intégrations sœurs : le téléphone admin choisi dans Outdoor Brief est proposé à l'installation de Partition Map. Le code de Partition Map est inchangé.

## [0.4.0] - 2026-11-21

### Modifié
- Module commun `admin_phone.py` passé en **MODULE_VERSION 1.1.0**, copié tel quel depuis ha-sdr (commit dfc42ab, SHA-256 `32b3619e…e1f9`, vérifié par un test).
- **Le téléphone admin peut être un service** `notify.<service>` **ou une entité notify**, envoyée via `notify.send_message`. Les alertes partent par `async_notify_admin` ; un échec d'envoi est seulement journalisé.
- Le formulaire propose aussi les entités notify de l'application mobile.
- **Notifications en français : virgule décimale**, par exemple « 92,8 % utilisé (200 Go sur 216 Go, 15,5 Go libres) ». En anglais, le point est conservé.
- Notifications vers un service `notify.mobile_app_*` : ajout de `notification_icon: mdi:harddisk`, affiché par Android et ignoré par iOS.

### Corrigé
- **Panneau après une mise à jour** : le navigateur gardait l'ancien module JS, puisque l'élément personnalisé ne peut pas être redéfini et que `?v=` ne suffit pas. La commande WebSocket renvoie maintenant la version ; si elle diffère de `PANEL_VERSION`, le panneau recharge la page une fois, puis affiche un bandeau « Recharge la page ». Un test vérifie que `PANEL_VERSION` correspond à la version de l'intégration.

## [0.3.0] - 2026-11-20

### Ajouté
- Panneau : bouton **Unités : Go / Gio** pour basculer entre base 1000 (comme Home Assistant) et base 1024 (comme Proxmox et la plupart des hyperviseurs). Le choix est mémorisé dans le navigateur.
- Taille de chaque disque affichée dans les deux unités, par exemple `34,0 Gio (36,5 Go)`.
- Note explicative sous la légende : écart d'environ 7,4 % entre les deux bases, avec un exemple pris sur le premier disque. Les tailles sont lues à l'octet près, seul l'affichage est arrondi.

### Modifié
- Panneau : unités et séparateur décimal selon la langue (`Go`/`Gio` et virgule en français, `GB`/`GiB` et point en anglais).

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
