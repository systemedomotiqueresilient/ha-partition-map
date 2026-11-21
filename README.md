<img src="custom_components/partition_map/brand/icon.png" alt="" width="96" align="right">

# Partition Map

![Version](https://img.shields.io/badge/version-0.4.1-blue)

Vue façon GParted des disques et partitions de Home Assistant OS : partitions orphelines, espace non alloué, slots A/B, sur un seul écran.

La carte « Stockage » de Home Assistant ne montre que la partition de données active. Après un « Déplacer le disque de données », l'ancienne partition reste sur le disque de démarrage, non montée, et l'espace ajouté en agrandissant un disque virtuel peut rester non alloué. Rien de tout ça n'apparaît dans l'interface. Partition Map l'affiche.

## Ce que ça montre

- Chaque disque avec ses partitions à l'échelle, dans l'ordre réel sur le disque
- Le rôle de chaque partition HAOS : boot, noyau et système (slot A/B, actif ou inactif), overlay, données
- L'occupation de la partition de données active
- **Les partitions orphelines** : ancienne `hassos-data` (label `hassos-data-old`) non montée
- **L'espace non alloué**, par exemple après l'agrandissement d'un disque dans Proxmox
- Les tailles en **Go** (base 1000, comme le reste de Home Assistant) ou en **Gio** (base 1024, comme Proxmox), au choix avec le bouton « Unités ». Un disque de 34 Gio dans Proxmox s'affiche 36,5 Go dans Home Assistant : c'est la même capacité, comptée dans une autre base.

Un capteur binaire `Partition orpheline` (catégorie diagnostic) passe à `on` quand de l'espace mort est détecté. Ses attributs donnent les partitions concernées, l'espace mort et l'espace non alloué en octets.

## Alertes de stockage

Partition Map surveille l'occupation de la partition data active et, si l'option est activée, des stockages réseau (partages de sauvegarde et de médias) :

- un capteur **Occupation** (%) par stockage, avec les octets utilisés, totaux et libres en attributs ;
- une alerte à **85 %** (avertissement) puis à **95 %** (critique), seuils réglables dans les options ;
- une seule notification par franchissement de seuil ; l'alerte se réarme quand l'occupation redescend de 2 points sous le seuil ;
- les niveaux sont mémorisés : un redémarrage de Home Assistant ne renvoie pas la même alerte ;
- une notification persistante dans tous les cas, plus le **téléphone admin** s'il est défini. Le titre contient le nom d'hôte, par exemple `⚠️ HAOS-Proxmox-LENOVO - Stockage presque plein`. Le tag `partition_map_<stockage>` fait remplacer la notification précédente sur le téléphone ;
- une alerte unique quand une partition orpheline apparaît.

## Téléphone admin (convention commune)

Le téléphone admin est la cible de notification de l'administrateur, partagée par convention entre mes intégrations (Sentinel Report, Deferred Restart, Entity Inventory, Package Keeper, Outdoor Brief, Partition Map) :

- chaque intégration crée **sa propre** entité diagnostic « Téléphone admin » (`<entry_id>_admin_notify_target`) ; son état et son attribut `notify_service` contiennent le service choisi ;
- la cible peut être un service (`notify.mobile_app_…`) ou une entité notify de l'application mobile ;
- à l'installation, le champ est **prérempli** avec la valeur déjà définie par une autre de ces intégrations. Si plusieurs valeurs différentes existent, elles sont proposées dans une liste ; sinon, ce sont les services `notify.mobile_app_*` disponibles ;
- la valeur est **copiée** dans la configuration de Partition Map : elle reste valable si l'autre intégration est supprimée ;
- elle se modifie ensuite par **Paramètres → Appareils et services → Partition Map → Configurer** ;
- rien n'est jamais écrit dans une autre intégration.

Le module `admin_phone.py` (version 1.2.0) est copié tel quel depuis le dépôt de référence `ha-sdr` ; il ne se modifie jamais dans Partition Map.

Partition Map est **en lecture seule** : aucune action sur les disques.

## Prérequis

- Home Assistant OS ou Supervised (les données viennent du Supervisor)
- Home Assistant 2025.3 ou plus récent

## Installation

### HACS (dépôt personnalisé)

1. HACS → ⋮ → Dépôts personnalisés → ajoute l'URL de ce dépôt, type **Intégration**
2. Installe **Partition Map** et redémarre Home Assistant
3. Paramètres → Appareils et services → Ajouter une intégration → **Partition Map**

### Manuelle

Copie `custom_components/partition_map` dans `/config/custom_components/`, redémarre, puis ajoute l'intégration.

Le panneau **Partition Map** apparaît dans la barre latérale (administrateurs uniquement).

## Fonctionnement

L'intégration lit le Supervisor : l'occupation toutes les 5 minutes, la table des partitions toutes les 30 minutes ou à la demande avec le bouton « Actualiser ».

- `/hardware/info` : disques (UDisks2) et périphériques bloc (udev). Les attributs udev donnent pour chaque partition son nom GPT, sa position, sa taille et son type de système de fichiers, y compris les partitions sans système de fichiers comme `hassos-bootstate`. Les points de montage viennent d'UDisks2. Les deux sources sont reliées par le numéro de série du disque.
- `/host/disks/default/usage` : occupation de la partition de données active.
- `/mounts` et `/host/disks/<montage>/usage` : occupation des stockages réseau.
- `/host/info` : nom d'hôte affiché dans les alertes.

> L'accès à `/hardware/info` passe par le client « passthrough » interne de l'intégration `hassio`, faute de module matériel dans `aiohasupervisor`. Cette API interne peut changer d'une version de Home Assistant à l'autre.

## Développement

```bash
pip install -r requirements_test.txt
pytest --cov
ruff check custom_components/ tests/
```

Voir aussi [CHANGELOG.md](CHANGELOG.md), [ROADMAP.md](ROADMAP.md) et [CLAUDE.md](CLAUDE.md).

## Tester l'analyse hors Home Assistant

```bash
# Sur l'hôte HAOS (console Proxmox → login) :
ha hardware info --raw-json > /mnt/data/supervisor/share/hw.json

# Sur ton poste :
python3 tools/check_layout.py hw.json
```

`layout.py` ne dépend pas de Home Assistant : il se teste avec n'importe quel export `ha hardware info --raw-json`.

## Licence

MIT
