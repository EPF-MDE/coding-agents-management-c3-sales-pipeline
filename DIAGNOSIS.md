# Diagnostic — Écart de revenu mensuel pour S-014

## Cause

`parse_amount` (src/pipeline/parse.py) utilise une regex qui s'arrête au
premier groupe de chiffres. Les exports du partenaire écrivent les montants
supérieurs à 1000 avec une espace insécable comme séparateur de milliers
(ex. « 1 321,49 » = 1321,49 €). La regex traite cette espace comme un
caractère non reconnu, ne capture que « 1 », et le reste du montant est
silencieusement perdu — aucune erreur, aucune alerte. S-014 est la seule
store alimentée par cet exportateur, ce qui explique pourquoi elle seule
est touchée, et uniquement les jours où au moins une transaction dépasse
1000 €.

## Ce qui m'a mis sur la piste

Le rapport de bug lui-même écartait déjà deux explications simples : le
nombre de lignes correspondait (420/420) et aucun doublon n'était filtré,
donc rien n'était perdu ni compté deux fois. Le fait que **les autres**
stores correspondaient au centime près écartait aussi un bug dans la
logique de calcul partagée (la formule de remise) — un bug dans du code
partagé toucherait tout le monde, pas une seule store.

Ma première vraie hypothèse était fausse, et je la garde car j'ai failli
m'y arrêter : la colonne `quantity` est parsée et stockée mais jamais
utilisée dans `normalise()` pour calculer `net_amount`. Ça collait avec
tous les symptômes de Claire (la plupart des jours bas, quelques-uns
exacts, seule S-014 touchée) si `amount` dans partner_export voulait dire
« prix unitaire » alors que dans les exports POS, `amount` voulait dire
« total de la ligne ». J'ai vérifié cette hypothèse en comparant la
distribution de `quantity` entre les sources plutôt que de me fier à la
cohérence apparente : les sources POS ont la même répartition de quantités
(1 à 4) et pourtant elles sont exactes — donc ignorer `quantity` ne peut
pas être la cause. Hypothèse abandonnée.

La vraie cause est apparue presque par accident, en écrivant un script
jetable pour recalculer le total de S-014 à la main :
`Decimal(amount.replace(',','.'))` plantait avec une erreur
`ConversionSyntax` sur cinq lignes. En affichant les valeurs brutes, j'ai
vu `'1\xa0321,49'` — une espace insécable que je n'avais pas remarquée en
lisant le CSV visuellement. Tester `parse_amount()` directement sur cette
chaîne l'a confirmé : elle retourne `Decimal('1')` au lieu de
`Decimal('1321.49')`.

## Pistes écartées

- **Lignes manquantes ou dupliquées** — le nombre de lignes et
  `duplicates_skipped` correspondaient aux chiffres de Claire ; rien à
  expliquer de ce côté.
- **Bug partagé dans le calcul de remise** — s'applique identiquement à
  toutes les stores ; les autres stores avec remises correspondent
  exactement, donc la formule elle-même n'est pas en cause.
- **Colonne `quantity` inutilisée** — hypothèse plausible au vu des
  symptômes, mais les sources POS l'ignorent aussi et sont correctes,
  donc ce n'est pas l'élément différenciant.

## Où cette découverte doit être consignée

Dans le code : la regex de `parse_amount` aurait dû couvrir la gamme de
formats d'export déjà documentée (le commentaire du module liste déjà
trois formats attendus) mais a manqué le séparateur de milliers. Ce n'est
pas un trou dans la spécification — rien n'indique que les séparateurs de
milliers ne devraient pas apparaître — c'est une implémentation incomplète
d'une règle que le code prétend déjà gérer.

## Temps

Est-ce que ça a pris plus d'1h30 : [ta vraie réponse]


# Diagnosis — S-014 monthly revenue mismatch

## Cause

`parse_amount` in `src/pipeline/parse.py` uses a regex
(`[-+]?[0-9]+(?:[.,][0-9]{1,2})?`) that does not recognise the non-breaking
space (`\xa0`) used as a thousands separator in the `partner_export` source
file (French format, e.g. `"1 321,49"` meaning 1321.49 euros). The regex
matches only the digits before the separator, so any amount of 1000 or
above is silently truncated (`"1 321,49"` → `1`) instead of raising an
error. S-014 is the only store fed by `partner_export_2026-08.csv`, which
is why it is the only one affected.

## What pointed me at it

The bug report ruled out missing rows and duplicates (transaction count
matched, `duplicates_skipped == 0`). Comparing `quantity` distributions
between `partner_export` and the POS sources ruled out the unused
`quantity` column as a cause, since POS sources ignore it too and are
unaffected. Manually re-running `python -m pipeline report --store S-014`
reproduced the exact buggy total (50043.47). Isolating failing rows during
manual parsing surfaced `ConversionSyntax` errors on values containing
`\xa0`, which directly pointed to the thousands-separator handling in
`parse_amount`.

## Ruled out

- Missing or duplicated transactions (count and dedup stats match).
- The discount formula itself (applied uniformly, other stores with
  discounts reconcile exactly).
- The unused `quantity` column (POS sources also ignore it and are correct).

## Where this finding belongs

This belongs in the code structure: `parse_amount`'s regex should be
extended to recognise thousands separators (space and non-breaking space),
which is what the fix does; it is not a specification or documentation gap,
since the module's own comment already anticipated multiple exporter
formats but missed this one.

## Time

Did this take more than 1h30: YES