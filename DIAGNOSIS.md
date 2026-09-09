
## Symptôme
Le revenu mensuel du magasin S-014 est sous-évalué de 6188,62 € (50 043,47 €
rapportés contre 56 232,09 € réels), alors que le nombre de transactions
(420) correspond exactement.

## Cause
`parse_amount` dans `pipeline.parse` utilise un regex qui ne reconnaît pas
l'espace comme séparateur de milliers utilisé par l'exportateur du
partenaire (ex. "1 321,49"). Le regex s'arrête au premier caractère non
numérique et non-`.`/`,`, donc il ne capture que "1" et perd le reste du
montant, silencieusement (pas d'exception, pas d'alerte).

## Ce qui a été éliminé
- Perte/duplication de transactions dans `load` : le compte (420) est
  correct des deux côtés, donc écarté.
- Erreur sur un jour ou une transaction isolée : l'écart est réparti sur
  plusieurs jours, donc écarté.
- Changement côté exportateur partenaire : confirmé sans changement par
  Claire, donc écarté.
- Bug dans `transform` (calcul de la remise) : les montants bruts étaient
  déjà faux avant la remise, donc le problème est en amont, dans `parse`.

## Fix
Le regex d'extraction du montant accepte maintenant les espaces internes
comme séparateur de milliers, retirés avant conversion en `Decimal`.

## Où ça aurait dû être détecté
Dans la spécification du format d'export partenaire : rien ne documentait
que les montants au-delà de 999 utilisent un séparateur de milliers, donc
`parse.py` n'avait aucune raison de le prévoir.

## Temps
1 h 30 passé dessus