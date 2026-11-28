# Roadmap

## Fait
- 0.1.0 : vue façon GParted, partitions orphelines, espace non alloué, diagnostics.
- 0.2.0 : téléphone admin (convention commune), alertes d'espace avec seuils et hystérésis, stockages réseau.
- 0.3.0 : bouton d'unités Go / Gio dans le panneau.
- 0.4.0 : admin_phone 1.1.0 (service ou entité notify), virgule décimale en français, rechargement automatique du panneau après une mise à jour.
- 0.4.1 : admin_phone 1.2.0 (Outdoor Brief ajouté aux intégrations sœurs).
- 0.5.0 : niveau de détail du tableau (Simple / Détaillé).
- 0.6.0 : admin_phone 1.3.0, manifest et hacs.json au modèle commun, zip de release, tolérance à une indisponibilité passagère du Supervisor.

## Prochaines étapes
- [ ] Brique du Hub SDR (socle hub_sdr de ha-sdr) : Partition Map est la première brique pilote prévue ; en attente du feu vert de Mathieu (note 03 d'Evernote).
- [ ] Tester en conditions réelles sur HAOS Proxmox LENOVO (2 disques, BackUP_HAOS en NFS).
- [ ] Réparation (Repairs) quand une partition orpheline est détectée, avec la marche à suivre pour récupérer l'espace (sans action automatique).
- [ ] Ajouter automatiquement les capteurs des montages réseau créés après l'installation (aujourd'hui : rechargement nécessaire).
- [ ] Notification de retour à la normale (optionnelle) et effacement de la notification sur le téléphone (`clear_notification` + tag).
- [ ] Panneau : utiliser les seuils configurés pour colorer les barres (aujourd'hui 85/95 fixes côté interface).
- [x] Icône (brand/) et workflows hassfest, HACS et tests prêts.
- [x] Publication GitHub (dépôt public `systemedomotiqueresilient/ha-partition-map`) et installation par HACS en dépôt personnalisé.
- [ ] Soumission au catalogue HACS par défaut.
- [x] Module de référence publié dans ha-sdr (1.0.0, puis 1.1.0 par Entity Inventory) ; Partition Map en 1.1.0 depuis la 0.4.0.

## Hors périmètre
- Toute action sur les disques (formatage, suppression, redimensionnement) : Partition Map reste en lecture seule.
- Toute connexion à un service tiers.
