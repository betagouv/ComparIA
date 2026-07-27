# Plan d’implémentation — personnalisation des couleurs et de l’URL d’accueil

Ticket de référence : [#494 — Branding configuration](https://github.com/betagouv/ComparIA/issues/494)

## Périmètre retenu

Ce lot couvre :

- quatre couleurs configurables : primaire et secondaire, chacune pour les thèmes clair et sombre ;
- une URL d’accueil utilisée comme destination du logo et du nom de la plateforme ;
- l’édition de ces valeurs dans `/admin/customization` ;
- leur application à l’ensemble de l’interface publique et du back-office.

Le nom et le logo sont déjà administrables sur la branche `next`. Les typographies et le message d’accueil en Markdown restent hors périmètre de ce lot.

## État du socle sur `next`

La dépendance structurante citée dans le ticket existe déjà :

- `app_settings` est une ligne singleton en base PostgreSQL ;
- `GET/PATCH /admin/settings` permet de lire et modifier la configuration ;
- `GET /auth/config` expose la partie publique au frontend ;
- la configuration est mise en cache dans Redis et invalidée après modification ;
- `/admin/customization` gère déjà le nom, le logo et l’objectif de votes ;
- le layout racine charge la configuration publique pendant le rendu serveur.

Il n’est donc pas nécessaire de créer un second stockage de configuration ni un nouvel endpoint public.

## Modèle de données et contrat API

### 1. Migration Alembic

Ajouter cinq colonnes à `app_settings` :

| Colonne | Type | Valeur par défaut |
|---|---|---|
| `primary_color_light` | chaîne non nulle | `#6464F3` |
| `primary_color_dark` | chaîne non nulle | `#9898F8` |
| `secondary_color_light` | chaîne non nulle | `#FF9575` |
| `secondary_color_dark` | chaîne non nulle | `#FFCC00` |
| `homepage_url` | chaîne nullable | `NULL` |

`NULL` pour `homepage_url` conserve le comportement actuel : lien vers la racine locale `/`.

La valeur primaire claire reste `#6464F3`, déjà utilisée à la place de `#6A6AF4` car elle respecte le contraste AA avec du texte blanc. Les valeurs sombres reprennent la maquette et assurent un contraste suffisant sur le fond sombre.

### 2. Modèles SQLModel/Pydantic

Étendre `AppSettings`, `AppSettingsPublic` et `AppSettingsPatch`.

Validation côté serveur :

- couleurs strictement au format `#RRGGBB`, puis normalisées en majuscules ;
- chaîne vide pour l’URL normalisée en `NULL` ;
- URL absolue HTTPS uniquement, avec longueur maximale raisonnable ;
- rejet des schémas `javascript:`, `data:`, `file:` et des valeurs relatives ;
- limites explicites de longueur afin de ne pas dépendre uniquement du type SQL.

La validation stricte des couleurs est aussi une protection contre l’injection CSS, puisque les valeurs seront rendues dans une feuille de style générée.

### 3. Endpoints existants

Étendre :

- `GET /admin/settings` avec les cinq champs ;
- `PATCH /admin/settings` pour leur modification atomique ;
- `GET /auth/config` avec les quatre couleurs et `homepage_url`.

Conserver les protections administrateur existantes et l’invalidation Redis existante. Régénérer ensuite `frontend/src/lib/generated/admin.ts` depuis les modèles Pydantic.

## Application du thème

### 4. Introduire des jetons sémantiques

Dans `frontend/src/css/app.css`, introduire des variables stables :

- `--brand-primary`;
- `--brand-primary-hover`;
- `--brand-primary-active`;
- `--brand-primary-contrast`;
- `--brand-primary-soft`;
- `--brand-primary-softest`;
- `--brand-secondary`;
- `--brand-secondary-text`.

Les variables DSFR et Compar:IA actuellement consommées (`--blue-france-main-525`, les variantes d’interaction et `--cg-orange`) deviennent des alias de ces jetons. Les couleurs UnoCSS `primary`, `light-primary`, `very-light-primary` et la nouvelle couleur `secondary` pointent elles aussi vers ces jetons.

Cette couche d’indirection évite de modifier les dizaines de composants qui utilisent déjà les classes `text-primary`, `bg-primary` ou `border-primary`.

### 5. Construire les variantes accessibles

Créer un petit utilitaire frontend pur qui, à partir des quatre couleurs :

- calcule les variantes hover/active ;
- choisit noir ou blanc pour `--brand-primary-contrast` selon le meilleur ratio ;
- produit des surfaces primaire légère/très légère ;
- produit une variante `--brand-secondary-text` contrastée pour les usages textuels.

La couleur secondaire brute reste disponible pour les éléments décoratifs et graphiques. Les rares usages actuels de `text-orange` doivent migrer vers `text-secondary-text` afin que la couleur choisie ne rende pas du texte illisible.

Les contrôles doivent garantir :

- 4,5:1 pour le texte normal et les libellés interactifs ;
- 3:1 pour les grands textes, icônes et bordures significatives ;
- un focus visible indépendant de la couleur de marque.

### 6. Injecter les variables dès le rendu serveur

Étendre `AuthConfig` dans le layout racine et rendre une feuille de style de thème dans le `<head>` à partir de données déjà validées par le backend.

La feuille doit contenir :

- les variables claires pour `data-fr-theme="light"` ;
- les variables sombres pour `data-fr-theme="dark"` ;
- un fallback `data-fr-theme="system"` avec `prefers-color-scheme`.

Le rendu dans le `<head>` évite un flash avec les couleurs par défaut avant l’hydratation Svelte. Il faut vérifier la compatibilité de cette stratégie avec la politique CSP du déploiement ; si une CSP à nonce est activée, le style généré devra recevoir le nonce plutôt que d’élargir `style-src`.

## Back-office

### 7. Étendre `/admin/customization`

Organiser le formulaire dans l’ordre suivant :

1. nom de la plateforme ;
2. URL de la page d’accueil ;
3. logo ;
4. couleurs ;
5. objectif de votes.

La section « Couleurs de la plateforme » contient :

- Primaire (thème clair) ;
- Primaire (thème sombre) ;
- Secondaire (thème clair) ;
- Secondaire (thème sombre).

Chaque couleur utilise un composant réutilisable composé de :

- un `<input type="color">` utilisable au clavier ;
- un champ texte hexadécimal associé ;
- un libellé visible ;
- une aide et un message d’erreur reliés avec `aria-describedby`.

Les deux contrôles restent synchronisés. La mise en page passe de deux colonnes sur écran large à une colonne sur mobile.

Le champ `type="url"` « URL de la page d’accueil » est placé après le nom de la plateforme, avec une aide précisant que cette adresse est ouverte lorsque l’utilisateur clique sur le logo ou le nom de la plateforme.

Le formulaire doit :

- valider avant envoi et afficher les erreurs par champ ;
- désactiver l’enregistrement pendant la requête ;
- proposer « Annuler les modifications » pour restaurer les dernières valeurs chargées ;
- afficher l’aperçu dans les deux thèmes ou, au minimum, permettre de prévisualiser chaque paire sans l’enregistrer ;
- mettre à jour le contexte frontend après succès pour que le changement soit visible sans rechargement complet.

Ajouter les libellés dans les traductions d’administration françaises et anglaises, avec le français comme référence produit.

## URL d’accueil

### 8. Centraliser la destination de marque

Ajouter une fonction ou valeur dérivée unique :

```text
homepageHref = config.homepage_url ?? resolve("/")
```

L’utiliser dans :

- le logo et le nom du `NavBar` de l’arène et du back-office ;
- le logo et le nom du `Header` des pages publiques.

Le footer institutionnel ne doit pas être redirigé automatiquement : son logo représente l’institution, pas la marque de la plateforme.

Conserver un comportement de navigation cohérent pour les URL internes et externes. Si une nouvelle fenêtre est conservée dans l’arène, annoncer explicitement ce comportement dans le titre accessible et ajouter les attributs `rel` appropriés.

## Tests et vérifications

### 9. Backend

- migration montante et descendante ;
- valeurs par défaut pour une instance existante ;
- acceptation et normalisation des quatre couleurs ;
- rejet des formats hexadécimaux invalides et des charges d’injection CSS ;
- acceptation de `NULL` et d’une URL HTTPS ;
- rejet des URL non sûres ;
- présence des champs dans les réponses admin et publique ;
- invalidation du cache après mise à jour.

### 10. Frontend

- tests unitaires du calcul des variantes et des ratios de contraste ;
- tests du CSS produit pour les thèmes clair, sombre et système ;
- test du composant de couleur : clavier, synchronisation, erreur explicite ;
- test du formulaire : chargement, annulation, enregistrement et erreur API ;
- test de navigation du logo/nom avec et sans URL personnalisée ;
- test Playwright des deux thèmes, sans flash de couleur au chargement ;
- audit axe/Playwright sur la page d’administration ;
- vérification visuelle des pages les plus exposées : accueil, arène, classement, connexion, invitation et back-office.

Commandes de contrôle prévues :

- lint et vérification Svelte/TypeScript avec `pnpm` ;
- tests unitaires frontend ;
- tests backend ;
- tests Playwright ciblés ;
- migration Alembic sur une base vide puis sur une base contenant déjà `app_settings`.

## Découpage conseillé

1. Migration et modèles de validation.
2. Extension des réponses admin/publique et régénération des types.
3. Jetons de thème, calcul des variantes et injection SSR.
4. Formulaire d’administration accessible.
5. Centralisation de l’URL du logo/nom.
6. Tests d’intégration, contrôle des contrastes et revue visuelle.

## Critères d’acceptation

- Un administrateur peut enregistrer quatre couleurs hexadécimales et une URL HTTPS.
- Les valeurs persistent après redémarrage et sont isolées à l’instance.
- Les thèmes clair et sombre utilisent chacun leur paire de couleurs.
- Il n’y a pas de flash avec le thème par défaut au chargement SSR.
- Le logo et le nom conduisent à l’URL configurée, ou à `/` si elle est vide.
- Une valeur invalide est refusée côté serveur même si le contrôle frontend est contourné.
- Les contrastes RGAA AA sont maintenus pour le texte et les contrôles.
- Le changement n’ajoute aucune dépendance propriétaire ni nouvelle dépendance frontend.
- Le comportement existant du nom, du logo, de l’authentification et de l’objectif de votes reste inchangé.

## Décisions appliquées

1. Les couleurs sombres par défaut reprennent la maquette : `#9898F8` et `#FFCC00`.
2. Le comportement de navigation existant est conservé : depuis l’arène, le lien de marque s’ouvre dans un nouvel onglet avec une annonce accessible et `rel="noopener"` (complété par `external` lorsque l’URL est externe) ; ailleurs, il s’ouvre dans l’onglet courant.
