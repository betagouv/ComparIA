# Protection des données — décisions et exploitation

Ce document complète les contrôles techniques du dépôt. Il ne remplace ni le
registre des traitements, ni une analyse juridique, ni l'avis du délégué à la
protection des données (DPD).

## Principes appliqués par l'application

- L'acceptation des modalités est enregistrée côté serveur avec la version et
  l'empreinte du document publié. Une acceptation absente ou obsolète est
  refusée par l'API.
- La participation à l'arène comprend nécessairement la collecte et la
  réutilisation des conversations et votes pour la recherche, l'évaluation et
  l'amélioration du service. L'interface présente cet ensemble comme une
  condition de participation, et non comme un consentement facultatif au sens
  du RGPD.
- La mesure d'audience reste un choix distinct et facultatif. Son refus ou son
  retrait ne doit jamais empêcher l'accès à l'arène ni modifier les conditions
  de participation.
- Les journaux techniques ne doivent contenir ni question, ni réponse de
  modèle, ni résultat de recherche web.
- La publication d'un export brut est désactivée par défaut. Elle nécessite une
  action explicite et une revue préalable.
- La mesure d'audience ne doit pas démarrer sans configuration valide, choix
  facultatif effectivement recueilli et paramétrage validé. Une éventuelle
  exemption de consentement doit être documentée par le responsable de
  traitement avant de modifier cette règle.

## Qualification du parcours de participation

L'action demandée avant l'entrée dans l'arène constate que la personne a pris
connaissance et accepté les conditions de participation. Elle ne doit pas être
présentée comme un « consentement RGPD » lorsque la recherche et la
réutilisation sont obligatoires pour participer : un consentement ne serait
alors pas librement donné.

Le responsable de traitement et le DPD doivent documenter une autre base
juridique adaptée pour chacune des finalités obligatoires, notamment pour la
recherche et la diffusion éventuelle de jeux de données. L'acceptation des
conditions d'utilisation ne crée pas à elle seule cette base juridique et ne
dispense ni de l'information des personnes, ni du respect de leurs droits.

Le choix relatif à la mesure d'audience doit être recueilli séparément. Il doit
pouvoir être refusé puis modifié aussi facilement qu'il a été accordé, sans
réutiliser l'acceptation des conditions de participation comme preuve de ce
choix.

Les anciens champs ou libellés techniques qui qualifient la réutilisation pour
la recherche de choix facultatif doivent être traités comme transitoires. Ils
ne doivent plus piloter l'accès à l'arène ou l'inclusion dans un export après
la validation et la migration de la base juridique par le responsable de
traitement.

## Décisions que le DPD et le responsable de traitement doivent renseigner

Avant une mise en production, consigner dans le registre des traitements :

1. la finalité et la base juridique de chaque traitement : fonctionnement de
   l'arène, authentification, sécurité, recherche, publication de jeux de
   données et, séparément, mesure d'audience facultative ; l'acceptation des
   conditions de participation ne doit pas être inscrite comme base juridique
   générique de ces traitements ;
2. les durées de conservation de chaque catégorie, ainsi que le délai de
   purge des sauvegardes et journaux ;
3. la liste des destinataires et sous-traitants effectivement activés pour
   chaque instance (fournisseurs de modèles, modération, recherche web,
   hébergement, observabilité et dépôt de données) ;
4. les lieux de traitement, garanties de transfert hors Espace économique
   européen et analyses de transfert applicables ;
5. l'adresse du DPD, le canal d'exercice des droits et le délai interne de
   traitement des demandes ;
6. la nécessité d'une analyse d'impact relative à la protection des données
   (AIPD), notamment au regard du volume, du texte libre, des publics mineurs
   possibles et des données sensibles susceptibles d'être saisies.

Les textes publiés dans l'interface ne doivent pas annoncer une anonymisation
ou une durée de conservation tant que le procédé et la durée n'ont pas été
validés et appliqués à toutes les copies, y compris les sauvegardes et exports.

## Revue avant publication d'un jeu de données

La personne responsable de la publication doit documenter :

- la version de l'extracteur et les filtres appliqués ;
- le résultat d'un contrôle humain et automatisé des données personnelles ;
- le caractère réellement anonyme ou, à défaut, le régime d'accès aux données
  personnelles et sa base juridique ;
- la procédure de retrait et de propagation d'une suppression aux copies déjà
  diffusées ;
- l'identité de la personne ayant autorisé la publication et la date de cette
  autorisation.

Un simple accès conditionné ou une pseudonymisation ne doit pas être présenté
comme une anonymisation.

## Vérifications d'exploitation

- Vérifier régulièrement que les variables des intégrations désactivées sont
  absentes et qu'aucun script tiers correspondant n'est chargé.
- Exécuter la purge de conservation selon un calendrier supervisé et conserver
  uniquement un compte rendu agrégé de son exécution.
- Tester périodiquement l'accès après acceptation des conditions de
  participation, le refus et le retrait de la mesure d'audience facultative,
  la révocation des sessions et l'effacement/anonymisation d'un compte fictif.
- Réexaminer les modalités et la notice à chaque nouvelle finalité, nouveau
  destinataire, transfert, catégorie de données ou modification substantielle.
