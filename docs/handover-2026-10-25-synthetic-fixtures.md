# T92 controlled synthetic fixtures — four-case handover

Archaeology PR425 merged with merge commit `e0cff951bd0e7b47be05af485110556d4bba4b19` after independent review and green CI. [derived: exact consumer readback, 2026-10-25] The supplied docs branch e5abf981 replaced the register with the string `actual CF3A`, contrary to its preservation claim. Goal2 reconstructed this handover on main08ab699f alongside T91, changing one evidence-limit cell and adding CORE-SYNTHETIC-1. All existing Rule/Source/Live cells, including merged G15 BM-7, are preserved; no runtime/vendor changes.

Four-fixture checklist:
- [x] CC7B role3 regular penalty: **isolated-synthetic**, source-derived6ECF call, actual6D4E(10,3,1), all controls/CF3A; stop before 82E0. No shootout or natural foul-award claim.
- [x] CC7B role4 free kick: **isolated-synthetic**, source-derived6F3E(1), actual signed range gate(x0,y−18,direction−1,product18),6D4E(11,4,1); all controls/CF3A; stop before 6FEA. No natural foul-award claim.
- [x] E022/E062: **integrated-synthetic**, copied slot10 word390→0 plus substitution-context flag; actual Enter→zero first-selection branch→message read214B:098A→Return→E44F readE61F. Stop there.
- [x] EA09/EC60: **isolated-synthetic**, copied outfield vacancy and explicit call frame; actual earlier eligibility/keeper checks return0, vacancy message waits/dismisses, EA09 AL0; stop before F067. No counter-local edit required.

All constructions and key/read/frame evidence: [merged report](https://github.com/diegoami/goal2-archaeology/blob/e0cff951bd0e7b47be05af485110556d4bba4b19/docs/requests/400-synthetic.md); [exact recipe](https://github.com/diegoami/goal2-archaeology/blob/e0cff951bd0e7b47be05af485110556d4bba4b19/notes/400-synthetic/recipe.md); [manifest](https://github.com/diegoami/goal2-archaeology/blob/e0cff951bd0e7b47be05af485110556d4bba4b19/notes/400-synthetic/delivery.json). Every original-byte payload stays in the [owner-only folder](https://drive.google.com/drive/folders/1b5VlP-nFHkWilG576gQj1P4iwERF9S7a). Final ZIP `t92-fixtures-v2-private.zip`,13842233 bytes, SHA256 `ab1864e3449a643bdc6119650e09b9d29e90ab01476aa9eace468d6834f9eeae`. Upload/readback and actual empty-cache replay passed; independent reviewer rebuilt all four from untouched bases and replayed saved inputs byte-identically. Initial shared-parent uploads were deleted after unexpected public-link access was detected; final folder/file owner-only permission readbacks verified.

Untouched base SHA256 `068a47729a3b1822ae6d3df7777eb99880bbcf74315e22098869ccaeac29ad28`. Runtime goal2 commit `5061474420b842ee98a4a1e4c9c2673c0764b1f2`; never import the active mutable goal2 checkout. Raw inputs:
- role3-r2: `0c096ee73d3be86dba4bb2f145762299a0086bdc8bc55298425e2b23033f31ae`
- role4-r2: `d776b78f0b8e559cfe42664dca4b4da3e430a211b825a4cbe73502c31a6fe48e`
- E062-r2: `a648f87fa04ae70224e5e6a052daa4998a14ee91d1b8c5f1fd5bd85f4ee08ed4`
- EC60-r1: `769934144d99e1dceb2a9015122401245bd2b2884320e9a960adef486b04188b`

In a clone of the merged archaeology source (not this consumer repository), with Python/Unicorn and authenticated rclone:
```sh
set -e
mkdir -p .cache/400-synthetic/readback
rclone copyto --drive-root-folder-id 1b5VlP-nFHkWilG576gQj1P4iwERF9S7a goal2drive:t92-fixtures-v2-private.zip .cache/400-synthetic/readback/t92-fixtures-v2-private.zip
cp .cache/400-synthetic/readback/t92-fixtures-v2-private.zip .cache/400-synthetic/t92-fixtures-v2-private.zip
unzip -n .cache/400-synthetic/readback/t92-fixtures-v2-private.zip -d .
python3 notes/400-synthetic/verify.py
tools/heavy.sh --slots 4 T92-replay -- python3 notes/400-synthetic/replay_all.py consumer-r1
```
Use a fresh replay suffix; outputs are append-only. Every attempt has 60 seconds including independent selector controls; standard four slots, no waiver. Both selectors independently exercise Up AC/Down B1/Enter, C, Esc, original no-key timeout and Space→actual CF3A blocking read→Return. Both refusals capture actual waits and dismissal. Raw snapshots preserve actual unsupported waits; no rewind or API save approximation. F029/F030 remain proposed. Natural unchanged-original acquisition remains open for all four cases on archaeology#400; synthetic coverage does not establish natural reachability or remove handlers.

Consumer prompt: check this branch against latest main/concurrent work, preserve every Live cell, review the four-fixture checklist and reproduce as useful. Open/reconcile a docs-only PR and ask the owner for its reviewer under archaeology process§14; goal2 owns review/merge. Any runtime adoption is a separate consumer task, not authorized/implemented here. Archaeology stops after this handover: no automatic inventory, collection or new task.

[derived: goal2 consumer replay, 2026-10-25] The final owner-only Drive file metadata and archive hash/size were checked. The unmodified verifier at reviewed56814197 passes70 immutable stopped-machine records. All four `goal2-consumer-r1` saved-input replays are byte-identical in steps, keys/events and constructed hashes, using the private bundle's pinned runtime50614744 under the standard four-slot limiter. Initial consumer setup errors missing the prescribed ZIP/readback paths were retained before the documented layout passed. These confirmations add neither runtime adoption nor natural reachability. Complete replay/failure receipts are retained locally and indexed on issue#394.
