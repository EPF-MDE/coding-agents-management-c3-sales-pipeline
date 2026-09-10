## Symptôme
Total S-014 août : 50 043,47 € calculé vs 56 232,09 € réconcilié par la Finance (écart 6 188,62 €).

## Cause
5 lignes sur 420 dans data/raw/partner_export_2026-08.csv contiennent des montants >= 1000 €
formatés avec un espace insécable (U+00A0) comme séparateur de milliers (ex. "1 321,49").
_AMOUNT_RE dans parse.py ([-+]?[0-9]+(?:[.,][0-9]{1,2})?) s'arrête au premier caractère non
numérique et ne capture que le premier chiffre : "1\xa0321,49" est tronqué à 1,00 €.
Vérifié ligne par ligne : la somme des 5 écarts (1320,49 + 1612,17 + 1016,60 + 962,56 +
1276,80) = 6 188,62 €, identique au centime à l'écart rapporté.

Ce qui a été écarté avant d'arriver à cette cause, avec preuve : troncature de séparateur
classique "." ou "," (aucun montant >= 1000 ne matchait ce motif — l'erreur de méthode ici
était de n'avoir cherché que "." et "," comme séparateurs, pas l'espace insécable), dérive
d'arrondi, quantity non multiplié, colonne/discount_pct à sens différent, montants négatifs
mal signés, doublons de txn_id, historique git, données égarées dans les autres sources,
constante cachée dans le code.

## Regression tests
- tests/test_pipeline.py::test_s014_august_total_matches_finance_reconciliation
- tests/test_parse.py::test_parse_amount_handles_nbsp_thousands_separator
Les deux échouent sur le code original, passent après fix (confirmé par git stash / stash pop).

## Fix
src/pipeline/parse.py : retrait de \xa0 avant le matching regex dans parse_amount(),
sans modifier _AMOUNT_RE elle-même (donc sans toucher à la gestion de "." et "," comme
séparateur décimal).

## Où le finding appartient
Au code : parse_amount() a une hypothèse de format implicite et non testée (aucun séparateur
de milliers, quel qu'il soit). C'est une omission dans la couverture de test des formats
d'entrée, pas un problème de spécification ou de logique métier.

## Note Outstanding
La suite de tests existante (17/17) ne pouvait pas détecter ce bug car aucun de ses cas ne
couvrait un montant >= 1000 dans le format partenaire — elle testait la fonction sur des
formats déjà connus, jamais sur les données réelles limites. La classe de bug est
"format d'entrée non couvert par les tests unitaires, invisible tant que la donnée réelle
ne l'exerce pas". L'enforcement qui l'aurait attrapé avant mise en prod (lien C2) : un test
de propriété (property-based test) sur parse_amount générant des montants aléatoires avec
différents séparateurs de milliers (., espace, espace insécable), ou plus simplement un
test de contrat vérifiant que la somme recalculée depuis n'importe quel fichier de
data/raw/ ne s'écarte jamais de plus de 0,01 € d'un total attendu fourni en fixture.

## Temps
A pris plus de 1h30 : oui
