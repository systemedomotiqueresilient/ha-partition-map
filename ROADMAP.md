# Roadmap

## Fait
- 0.1.0 : vue façon GParted, partitions orphelines, espace non alloué, diagnostics.
- 0.2.0 : téléphone admin (convention commune), alertes d'espace avec seuils et hystérésis, stockages réseau.
- 0.3.0 : bouton d'unités Go / Gio dans le panneau.
- 0.4.0 : admin_phone 1.1.0 (service ou entité notify), virgule décimale en français, rechargement automatique du panneau après une mise à jour.
- 0.4.1 : admin_phone 1.2.0 (Outdoor Brief ajouté aux intégrations sœurs).

## Prochaines étapes
- [ ] admin_phone 1.3.0 (reconnaissance ouverte des sœurs : marqueur `admin_phone_convention`, codeowners) : en attente du feu vert de Mathieu, voir le journal Evernote.
- [ ] Tester en conditions réelles sur HAOS Proxmox LENOVO (2 disques, BackUP_HAOS en NFS).
- [ ] Réparation (Repairs) quand une partition orpheline est détectée, avec la marche à suivre pour récupérer l'espace (sans action automatique).
- [ ] Ajouter automatiquement les capteurs des montages réseau créés après l'installation (aujourd'hui : rechargement nécessaire).
- [ ] Notification de retour à la normale (optionnelle) et effacement de la notification sur le téléphone (`clear_notification` + tag).
- [ ] Panneau : utiliser les seuils configurés pour colorer les barres (aujourd'hui 85/95 fixes côté interface).
- [x] Icône (brand/) et workflows hassfest, HACS et tests prêts.
- [ ] Publication GitHub (dépôt public `systemedomotiqueresilient/ha-partition-map`, release v0.4.1) puis ajout comme dépôt personnalisé dans HACS.
- [x] Module de référence publié dans ha-sdr (1.0.0, puis 1.1.0 par Entity Inventory) ; Partition Map en 1.1.0 depuis la 0.4.0.

## Hors périmètre
- Toute action sur les disques (formatage, suppression, redimensionnement) : Partition Map reste en lecture seule.
- Toute connexion à un service tiers.
