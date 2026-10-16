#!/usr/bin/env python3
"""[designed: T62] Strict ten-record E032 parity plus independent original-state/event checks.
Reuse the accepted comparator/schema and E033 entry probe; no second application caller.
Player/country bytes and final seeds are compared with the independent entry probe plus original B7FA.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import zlib
from watched_evidence import ROOT, SOURCE, stage
sys.path.insert(0, str(ROOT))


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def original_tail(probe):
    """[derived: merged E033 match.py _call; route_fixture 000E:6FF8] B7FA uses the same fixture pointer/frame.
    This verification-only continuation reuses Entry's machine, independently of Match._advance/_finish.
    """
    fix_off, fix_seg = probe.rd(0xA92B) + 8 * 20, probe.rd(0xA92D)
    ss, sp = probe.load + 0x3052, 0x3EC0
    for i, word in enumerate((0x6FFD, probe.seg(0x000E), fix_off, fix_seg)):
        probe.put(ss * 16 + sp + 2 * i, word.to_bytes(2, "little"))
    for reg, value in (("ss", ss), ("sp", sp), ("bp", 0x3EDE), ("ds", probe.DS),
                       ("cs", probe.seg(0x0791)), ("eip", 0xB7FA)):
        probe.set_reg(reg, value)
    probe.emulate(probe.lin("000E:6FFD"), 60)
    return {"players": probe.mem(probe.far(0xA91B), 3061 * 20),
            "countries": probe.mem(probe.far(0xA917), 129 * 0xBF),
            "seeds": [probe.rd(0x7B62), probe.rd(0x8336)]}


def strict_original(entry, raw, seed):
    """[derived: accepted E032 timing.py] Repeat its actual watchstart input and declared calibration write.
    Keep actual start identity/inputs in the strict record; menu-entry equivalence is checked separately.
    """
    from unicorn import UC_HOOK_CODE
    m = entry.WatchedMatch(raw)
    m.set_seed(seed)
    done = []
    def at_tick(uc, address, size, data):
        if done:
            return
        linear = m.DS * 16 + 0xA9FF
        old = m.mem(linear,4)
        uc.mem_write(linear,(20).to_bytes(4,"little"))
        m.inputs.append({"what":"delay calibration dword DS:A9FF/AA01, at the first 0791:970C entry",
                         "linear":linear,"old":old.hex(),"new":(20).to_bytes(4,"little").hex()})
        done.append(True)
    linear = m.lin("0791:970C")
    m.mu.hook_add(UC_HOOK_CODE,at_tick,begin=linear,end=linear)
    t,c = time.monotonic(),time.process_time()
    m.run(timeout_s=60)
    digest = hashlib.sha256("\n".join("%d %d %04x %04x" % d for d in m.draws).encode()).hexdigest()
    return {"seed":seed,"error":None,"stopped_at_board":m.stopped_at_board,"strays":list(m.strays),
            "cpu_s":time.process_time()-c,"wall_s":time.monotonic()-t,"start_record":"E011-r0001",
            "watchstart_sha256":hashlib.sha256(raw).hexdigest(),"inputs":m.inputs,"delay_count":20,
            "score":m.state()["score"],"ticks":len(m.tick_marks),"draws":len(m.draws),"draws_digest":digest,
            "statistics_raw":m.statistics(),"templates":dict(collections.Counter(str(c["template"]) for c in m.commentary()))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, choices=(1, 10), default=10)
    args = ap.parse_args(argv)
    folder = stage()
    sys.path.insert(0, str(folder / "experiments/E032-match-engine-inventory"))
    compare = module("watched_compare", folder / "experiments/E032-match-engine-inventory/compare.py")
    entry = module("watched_entry", folder / "experiments/E033-original-match-kit/entry_probe.py")
    stamps = module("watched_stamps", folder / "experiments/E033-original-match-kit/stamps.py")
    from goal2.engine.original_match import Image, Match, Fixture
    from goal2.engine.original_match.assets import reference_image
    raw = reference_image(ROOT / ".cache")
    image = Image.from_savestate(raw)
    # [derived: E033 section2] Menu images share team records but not every RNG word/calendar.
    # Use the SAME reference image for the independent entry; declare the identical fixture row.
    independent_image = Image.from_savestate(raw)
    address = independent_image.far(0xA92B) + 8 * 20
    independent_image.memory[address:address + 8] = bytes([0xFE,0,1,0,7,0,19,0])
    from goal2.game.state import _rewrite_zip
    data = _rewrite_zip(raw, {"Memory": zlib.compress(independent_image.memory_component())})
    refs = {}
    for name in ("timing-delay20-kickoff-20261015.jsonl", "timing-delay20-8seeds-20261015.jsonl"):
        loaded = compare.load(folder / "experiments/E032-match-engine-inventory/out" / name)
        if set(refs) & set(loaded):
            raise ValueError("duplicate reference seed across logs")
        refs.update(loaded)
    seeds = sorted(refs)[:args.seeds]
    if len(refs) != 10 or len(seeds) != args.seeds:
        raise ValueError("strict reference family must have ten unique seeds")
    candidate = {}; details = []
    for seed in seeds:
        t0, c0 = time.monotonic(), time.process_time()
        m = Match(image, Fixture(7, 19, index=21), managed=7, seed=seed, record_draws=True, delay_byte=0)
        independent = stamps.Independent(m.m)
        events = []
        for ev in m.events():
            events.append((ev.kind, ev.minute, ev.score, ev.data))
            if ev.kind == "decision":
                m.answer()
        result = m.result()
        if independent.expected() != stamps.kit_stamps(events):
            raise ValueError(f"seed {seed:#06x}: event stamps/order differ from original writes")
        # [designed] Independent reference is original entry/code, not a copy of the kit's returned fields.
        probe = entry.Entry(data, seed_override=seed).go(timeout_s=60)
        expected = original_tail(probe)
        after = Image(m.memory_component())
        got = {"players": bytes(after.memory[after.far(0xA91B):after.far(0xA91B) + 3061 * 20]),
               "countries": bytes(after.memory[after.far(0xA917):after.far(0xA917) + 129 * 0xBF]),
               "seeds": [int.from_bytes(after.memory[after.DS * 16 + o:after.DS * 16 + o + 2], "little")
                         for o in (0x7B62, 0x8336)]}
        if expected != got or result["seed_after"] != got["seeds"][0]:
            bad = [key for key in expected if expected[key] != got[key]]
            if result["seed_after"] != got["seeds"][0]:bad.append("result.seed_after")
            raise ValueError(f"seed {seed:#06x}: original post-match state differs: {bad}; seeds reference={expected['seeds']} kit={got['seeds']}")
        # [designed] Re-run strict E032 on its TRUE watchstart input. Never borrow reference identity/inputs.
        watchraw = (folder / ".cache/dl/d68e48c734a742a6-E011-r0001-watchstart.sav").read_bytes()
        rec = strict_original(entry,watchraw,seed)
        compare.validate(rec,f"fresh original seed {seed:#06x}")
        candidate[seed] = rec
        # [derived: E033] Explicit menu-entry equivalence: six measured outcomes, not an invented same-image claim.
        stats_rows = []
        for row in rec["statistics_raw"]:
            value = dict(row)
            field = "raw_bytes" if "raw_bytes" in row else "raw_words"
            label = row["row_label"]
            value[field] = (result["board"]["bars"][0 if label == "Possession" else 1]
                            if field == "raw_words" else result["board"]["statistics"][label.lower().replace(" ","_")])
            stats_rows.append(value)
        kit_fields = {"score":result["score"],"ticks":result["ticks"],"draws":result["draws"],
                      "draws_digest":result["draws_digest"],"statistics_raw":stats_rows,
                      "templates":dict(collections.Counter(str(c["template"]) for c in result["commentary"][-199:]))}
        differences = [key for key in compare.FIELDS if rec[key] != kit_fields[key]]
        if differences:
            raise ValueError(f"seed {seed:#06x}: kit differs from strict original: {differences}")
        details.append({"seed":seed, "players_sha256":hashlib.sha256(got["players"]).hexdigest(),
                        "countries_sha256":hashlib.sha256(got["countries"]).hexdigest(), "seeds":got["seeds"],
                        "event_order":True, "wall_s":round(time.monotonic()-t0,2)})
        print(f"state/events {seed:#06x}: PASS", flush=True)
    lines, ok = compare.check(refs, candidate, seeds, "identical")
    print("\n".join(lines))
    report = ROOT / ".cache" / f"watched-records-{time.time_ns()}.json"
    report.write_text(json.dumps({"source":SOURCE,"records":details,"strict_pass":ok},indent=2)+"\n")
    print(f"diagnostics: {report}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
