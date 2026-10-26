# Core pool names

[designed: owner #433/T136,2026-10-26] Pool identities use country-appropriate names consistently
across the Core desktop. The original uses one shared unassigned surname bank [confirmed:
F002/F007/F011; archaeology232 comment6200041267]. This presentation policy deliberately differs
from that original naming rule. It never writes an alias into guest memory or the Core payload.

## Coverage and identity

The existing `goal2/data/pool_names.json` remains unchanged:33 authored country lists, each
with80 surnames and initials. `goal2/data/pool_names_extended.json` adds the other95 countries.
Of those,94 profiles contain60 distinct surname spellings. Every family is used before any is
repeated; initials are deterministic and avoid an existing national player's complete name.
Every80-player pool has80 unique display names. Profiles follow full player IDs and the current
assigned country, including exchange and original regeneration. Custom country-name mismatches
and missing canonical data retain the original text.

[designed: owner2026-10-26, #433 comment6412181982] Myanmar is an explicit exception:80 complete
Burmese personal names, with no invented initial or surname split. The combinations are authored
from attested name components; they are fictional identities, not copied player biographies.
The [UK Passport Office naming guidance](https://www.gov.uk/government/publications/myanmar-burma-knowledge-base-profile/myanmar-burma-knowledge-base-profile)
explains why surname counting does not fit the usual Burmese convention.

Long surnames remain complete on the player card and in accessibility text. The pool strip may
elide a name before CAPS; caps and the case-sensitive role letter keep their own columns.

## Sources and selection

The extended profile resource includes a source record beside every selected surname:

- [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing), CC0-1.0, queried2026-10-26:
  family-name (`P734`) items linked to a person's citizenship (`P27`). Item IDs, the source
  spelling and the number of matching Wikidata attestations are recorded. These counts describe
  Wikidata coverage; they are **not population-frequency estimates**. The lists make no claim
  to reproduce national demographic proportions or a population-wide popularity order.
- [sigpwned/popular-names-by-country-dataset](https://github.com/sigpwned/popular-names-by-country-dataset),
  CC0, frozen at `eb62e13d4d62dd96cdfae79d293a02066352205f`. The profile records identify the
  source country and surname group. Only one primary romanization per group is considered;
  alternative spellings do not manufacture additional surname groups.

For Northern Ireland, Wales, Puerto Rico and the former Netherlands Antilles, the Wikidata
attestations instead use births in Belfast (`Q10686`), Cardiff (`Q10690`), San Juan (`Q41211`)
and Willemstad (`Q132679`), respectively. These are explicitly local samples, not claimed
territory-wide frequency rankings. Willemstad is a source within the former Antilles association;
no unrelated modern country is silently substituted for it.

Oman's profile is a curated selection of60 distinct Al- family suffixes attested in Omani
citizens' names. Each selected spelling links to an attesting Wikidata item. Common spacing and
hyphen variants are grouped during curation; the profile does not count them as extra families.

Curation rejects control characters, unresolved item labels, person/place/book links incorrectly
used as surnames, dynasty/house captions and non-name tribal captions. It filters explicitly
feminine spelling forms in Bulgarian, Polish and Icelandic profiles intended for the men's pool.
Names containing Latin characters unavailable in the existing CP437 presentation use a readable
Latin spelling; original source spellings remain in the evidence records. Accents, punctuation
and spacing variants are deduplicated before selecting60 spellings. Existing authored names are
not rewritten. No runtime name library, GPL dataset, downloaded game byte or extracted original
surname list is bundled in the extended profiles.

[designed: T136] Selection and romanization are goal2's presentation choices. A country-use
attestation is evidence of use, not proof that a spelling is equally common throughout a country.
Future corrections should retain provenance and independent named-country checks, rather than
repeating an indexing formula in both the implementation and its expected test output.

## Saves

The generated aliases are not saved. Reopening the same career with the same packaged policy
resolves the same names. Original F2 renames take precedence. The desktop records optional
explicit-rename fingerprints in its existing JSON header so that a deliberately chosen original-bank
name remains distinguishable from an automatically regenerated default. The guest payload and
Core save version do not change. Old saves without that intent cannot reveal an earlier manual
choice of an original-bank name; re-entering it through F2 records the choice. No alias or original
surname bank is serialized in the optional metadata.
