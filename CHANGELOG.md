# Changelog

## 3.0.0

- Promoted MEP Planner to the first stable 3.x release.
- Added a root `VERSION` file as the single source of truth.
- Backend, API health endpoint, administration page and GitHub update checker now use the same installed version.
- Updated Docker build contexts so the backend image embeds the root version file.
- Updated the interface fallback version, documentation and release commands.
- Preserved all v2.9.1 email and PDF language fixes.

## 2.9.1

- harmonisation complète du thème clair ;
- champs de recherche, listes déroulantes et boutons secondaires en palette violet clair ;
- traduction FR/EN centralisée de toute l’interface ;
- traduction des titres, statistiques, tableaux, filtres, calendriers, popups et paramètres ;
- ajout du choix séparé de langue pour les emails et PDF ;
- ajout de `COMMUNICATION_LANGUAGE` dans `.env_template` et `.env.example` ;
- README actualisé.

## 2.9.1

- Protection des paramètres par mot de passe administrateur défini dans `.env`.
- Sessions administrateur temporaires.
- Lien GitHub discret dans la barre latérale.
- Comparaison de la version installée avec la dernière release ou le dernier tag GitHub.
- Bloc À propos et état de mise à jour dans Paramètres.
- Boutons du thème clair adoucis avec un dégradé violet clair.
- Documentation et `.env_template` actualisés.

# Changelog

## 2.7.0

- thème clair et sombre mémorisé par navigateur ;
- interface français/anglais ;
- langue globale appliquée aux communications ;
- branding générique « My Company » ;
- retrait du nom de société des emails et PDF ;
- conservation du logo entreprise facultatif seul.

# Changelog

## 2.6.0

- Ajout du menu Paramètres.
- Ajout d'un logo et d'une identité d'entreprise complémentaires à MEP Planner.
- Persistance du branding entreprise dans SQLite et dans le volume Docker.
- Utilisation du logo entreprise dans l'interface, les emails et les PDF.
- Suppression de l'heure fictive 09:00 lorsque Redmine ne fournit pas d'horaire.
- Ajout du statut « Heure à préciser » et d'un filtre dédié.
- Calcul automatique de l'heure de fin à partir du temps estimé uniquement si une heure de début existe.
- Ajout de `.env_template`, `.gitignore`, d'un README GitHub et d'un script de sauvegarde.
- Version API 2.6.0.

## 2.9.1

- Fixed communication language propagation to automatic emails, manual resends and PDF reports.
- Email subjects, HTML content, plain-text fallback, PDF labels and filenames now follow the communication language setting.
