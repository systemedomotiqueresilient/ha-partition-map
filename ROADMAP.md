# Roadmap

## Fait
- 0.1.0 : vue façon GParted, partitions orphelines, espace non alloué, diagnostics.
- 0.2.0 : téléphone admin (convention commune), alertes d'espace avec seuils et hystérésis, stockages réseau.

## Prochaines étapes
- [ ] Tester en conditions réelles sur HAOS Proxmox LENOVO (2 disques, BackUP_HAOS en NFS).
- [ ] Réparation (Repairs) quand une partition orpheline est détectée, avec la marche à suivre pour récupérer l'espace (sans action automatique).
- [ ] Ajouter automatiquement les capteurs des montages réseau créés après l'installation (aujourd'hui : rechargement nécessaire).
- [ ] Notification de retour à la normale (optionnelle) et effacement de la notification sur le téléphone (`clear_notification` + tag).
- [ ] Panneau : utiliser les seuils configurés pour colorer les barres (aujourd'hui 85/95 fixes côté interface).
- [ ] Publication GitHub + HACS (dépôt `systemedomotiqueresilient/ha-partition-map`), workflows hassfest et HACS.
- [ ] Recopier `admin_phone.py` 1.0.0 dans Sentinel Report, Deferred Restart et Entity Inventory.

## Hors périmètre
- Toute action sur les disques (formatage, suppression, redimensionnement) : Partition Map reste en lecture seule.
- Toute connexion à un service tiers.
