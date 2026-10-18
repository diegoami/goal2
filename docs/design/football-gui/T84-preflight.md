# T84 player attributes: field and comparison contract

[designed: main contract, owner request 2026-10-19] Main must complete baseline/mock preflight before implementation dispatch. Preserve existing seven defaults. Checked against accepted tree b663 and archaeology pin 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb. F008 last change 8a804db5ef1db18ebe8b1b287293f6a5362e680e; F008 and E007 summarise unchanged from that accepted pin to current archaeology HEAD.

## Exact expanded columns

[designed] Squad defaults (7): XI, Player, Position, Ability, Energy, Confidence, Availability.
Pool defaults (7): ID, Player, Position, Ability, Energy, Confidence, Availability.
Append ID to squad only (pool already has it). Append these SAME thirty attributes to both tables, in this order:

1. Age
2. Caps
3. Goals
4. Height (in)
5. Foot
6. National position
7. Club position
8. Cards
9. Performance
10. Readiness
11. Keeping
12. Kicking
13. Tackling
14. Heading
15. Marking
16. Passing
17. Crossing
18. Feinting
19. Control
20. Dribbling
21. Shooting
22. Penalties
23. Hardness
24. Fitness
25. Leadership
26. Position tactic
27. Possession tactic
28. Passing tactic
29. Tackling tactic
30. Mark tactic

[designed] Expanded totals: Squad 38, Pool 37. Energy and morale/confidence already exist in defaults: do not duplicate them. Original named national position differs from broad Position group and warrants its own column. Tactic cells include compact Personal/Team source suffix; header/accessibility explains suffix. No extra profile, potential, peak age or unknown-byte columns. Metadata words in table; numeric original units for skills/hardness/fitness/leadership; descriptors in complete card. Performance shows No performance for sentinel and an explicitly labeled raw word otherwise; original bucket rendering remains unavailable until independently verified. Readiness uses established pre-match flags plus separate actual management context; never template DS screen mode. Named tables own horizontal scrolling; shell remains bounded. Shared complete card remains mandatory for selected incoming AND outgoing player on pool.

## Evidence matrix

[confirmed: F008 @8a804db, unchanged at accepted 0ef880 pin] All line references below are to archaeology findings/F008-the-player-screen-draws-12-skills-as-bars-derived-from-three-record-bytes.md (F) and experiments/E007-q009-player-screen/summarise.py (S). Source repository /home/diego/projects/goal2-archaeology. E007-r0009..r0012 provides 80 cards / 11200 checked values; 960 skill comparisons. Original fixtures stay private/untracked.

| Field | Exact source | References | Supported-domain guard / limits |
| --- | --- | --- | --- |
| Name/full ID | goaldat.player_names[id]; original initial [9B70]+id and surname [9B6C]+11*id | F19 | Full id 1..3060; record length20; selected id must belong to current roster/pool. Never mask to byte. |
| Age | record[1] | F20, S205 | Raw years byte; observed22..34; do not clamp to observed range. |
| Caps/goals | u16le record[8:10], record[10:12] | F21, S205 | Both bytes, counts0..65535 storage. New-game observations only zero. |
| Height | DS:0E46[+7]+DS:0E54[id%12] inches | F22, S102..104 | +7 in0..13; valid table bytes; show original feet/inches card, inches comparison. |
| Foot | two footed if +5 + +2 ==30; else DS:0F2C+6*DS:0E60[14*DS:0E7C[id%3] + +7] | F23, S107..114/207 | +7 in0..13; table indices within actual table domains; bounded Pascal string decoding, no arbitrary memory text. |
| National/club position | Pascal19 at DS:69B6+19*record[6/7] | F24, S208 | Codes0..13; invalid code explicitly unavailable. Byte distinction statically established; new-game observed equal. |
| Skills | existing skills.skills; class DS:6D25[12*+7+i], profile DS:6DCD[12*+5+class], value*(+4+1)//256 | F15..17, S131..145 | +7 in0..13; +5 in1..16 generated domain (0 supported by existing loader but not observed new-game); class in1..12; original ability<=253 gives0..25. Invalid domain unavailable rather than fabricated normalized values. |
| Hardness | h=(+5-(+3&1))&255; word DS:6EB4+16*DS:78C4[h]; bar h*14//16 | F26, S117..119/213 | h0..16; retain raw outside domain but no invented descriptor/bar. |
| Fitness | raw+D; word DS:6EB4+16*DS:78D5[D if E else0]; bar D*14//32 when E else0 | F26, S212/214; F018 | Descriptor D0..32 only; signed-negative E unavailable; exact injury special case. |
| Energy | raw+E; word DS:6EB4+16*DS:78F6[E]; bar E*14//32 | F26, S215; F018 | E0..32 for descriptor; E>=128 means signed unavailable, never healthy large bar. No unsourced rescaling. |
| Morale/confidence | raw+C; descriptor DS:78A3[min(C,32)]; bar C*14//32 only C<32 else0 | F26, S216; F019/F020 | Original descriptor saturates at32; raw byte retained; do not call percentage. Team morale aggregate separate. |
| Leadership | d=+3-+5; v=d%8, v//=2 if age<21; descriptor DS:7917[v]; bar v*14//7 | F26, S122..128/217 | d>=0 proven model domain; negative idiv remainder unresolved, unavailable rather than Python modulo substitution. |
| Four tactics | i1..4: personal flag +F bit(i+3); value bit(i-1) from personal+F if enabled else team byte; Pascal16 at DS:6AA0+32*i+16*value; GK special DS:0EA6/0EC6 for rows1/3 | F27, S180..191 | Managed team fallback from state.country_tactics, never stale countries[c][2D] or template. Expose Personal/Team source. Existing draft checkbox toggles do not publish effective state. |
| Mark tactic | blank national pos<2; +10&0x40 Protect zone Personal; else team bit7 text at DS:0E90+11*bit | F27, S192..198 | Pre-match context only; in-match opponent naming unresolved. Do not read stale template DS:0C1E. |
| Cards | +10 masks0x08 carried booking,0x10 booked,0x20 sent off | F25; F027 | Named flags, not invented total. Original icons statically established, E007 blank only. |
| Readiness | priority suspended0x80, E==0 injured, booked0x10, sent off0x20, substituted0x04, ready | F25, S157..177; accepted eligibility.info | Use accepted signed-energy availability too. Selection/bench is actual managed lineup context, not template screen context. |
| Performance | u16le+12; 0x7FFF sentinel blank | F25, S209; 1771:3827 | Nonblank original bucket rendering unresolved upstream; display an explicitly labeled raw word; original bucket interpretation remains unavailable, with no skill/rating scale inferred. |

[derived: accepted state adapter] Tables from _wrap_raw(state.vga,state.mem); live player bytes exclusively state.players[id]; managed tactics state.country_tactics. Never copy records from immutable template. Validate bounded Pascal string lengths and loaded table domains before decoding. Unsupported values remain explicitly unavailable with raw source where useful.

[confirmed: accepted PROVENANCE.md] players.py/savestate.py engine pin8760df9; energy/confidence/morale pin0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb. No engine edits required. Existing test_skills.py/test_p1_fidelity.py independently parse E007 bars; archaeology runtime/driver/playerscreen.py parses original card cells and E007 summarise compares their values. New comparisons should reuse observations as expected output, not compare decoder to itself.

[designed: unresolved] [Archaeology request #346](https://github.com/diegoami/goal2-archaeology/issues/346) requests focused original nonblank performance exploration (1771:3827 word signed/wrapped arithmetic, nine buckets, actual glyphs and representative probes). Match-context marking/status not needed for bounded pre-match card; avoid claiming reconstructed live original screen mode. Record+11 not a card attribute. +2/+3 peak age/potential remain inferred and are not comparison fields.
