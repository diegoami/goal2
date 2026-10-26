# Core pool names

[designed: owner #433/T136, scope corrected2026-10-26] The Core desktop reuses only the existing
33 authored T93 profiles: the canonical top32 countries plus Greece. The owner explicitly dropped
the128-country expansion. The original uses shared unassigned pool names [confirmed:
F002/F007/F011; archaeology232 comment6200041267]; the covered-country display policy is a
deliberate difference from that naming rule.

## Coverage

`goal2/data/pool_names.json` remains byte-for-byte unchanged. Each of its33 country profiles
supplies80 distinct surnames and80 initial/surname display names. No external surname corpus,
additional-country resource or fallback name generator is packaged. All unlisted countries
retain their current original names, including names changed by original regeneration.

Covered aliases follow the full player ID and assigned country across pool, recruitment, team,
cards, comparisons, suggestions, scorers and commentary. Browsing changes no guest memory,
CPU, original keys, RNG or Core payload. Original driver/oracle reads retain raw identities.
A custom country-name mismatch or unavailable canonical GOAL.DAT also retains original text.

Commentary retains the original surname-only format while resolving the full raw name, so
explicit rename fingerprints still apply. Competition scorer copies receive aliases only when
their full ID and copied name match the current record. Stale copies retain their original text.
History's current-player goals/caps entries resolve by full ID; older kept entries without IDs
retain their copied names rather than guessing identities. Counts and ordering stay unchanged.

The authored names fit the existing pool name/caps/role layout. Full identities remain visible
on cards and in comparisons, including accents. Existing case-sensitive role codes are preserved.

## Replacement players and renames

[designed: T136] A covered alias belongs to a full-ID/country slot. When the original replaces
that record with a new player, this version keeps the slot's display name while the original raw
name, age and attributes can change. This differs deliberately from original visible replacement
names. No alias is persisted as a new person-identity record; followup444 records possible later
identity-policy changes.

Explicit original F2 renames take precedence. A changed surname outside the original unassigned
bank keeps its own text. The desktop also records fingerprints of explicit original-bank choices,
so these are not mistaken for automatically regenerated defaults after reopening.

## Saves

Generated aliases are not saved. Reopening a career with the same packaged authored data resolves
the same covered names. Optional `display_name_intent` version1 in the existing JSON header stores
only full-player-ID→SHA256 fingerprints of explicit names. Guest payload and Core save version
remain unchanged, and old saves load without migration.

An old save without intent cannot distinguish a past manual choice of an original-bank name
from an automatically generated default. Re-entering that name through F2 records the choice.
Malformed or unsupported intent is rejected with the existing Cannot resume the core error;
followup444 records possible recovery work. No generated alias or original surname bank is
serialized in this metadata.
