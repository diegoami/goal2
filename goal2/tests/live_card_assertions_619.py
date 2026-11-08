"""[designed: #619] Independent UI checks of actual backend records; no raw output.

The accepted player_card decoder remains the display oracle. Build its input
from the actual event, without using the production live_cards projection.
"""
import copy
import hashlib
import json


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _expected(test, model, data, word, answer=None):
    from goal2.game.player_card import card
    records = {w: bytes.fromhex(encoded) for w, encoded in data['player_records']}
    view = copy.copy(model.state)
    view.players = list(model.state.players)
    view.country_tactics = data['tactics']
    for w, raw in records.items():
        view.players[w] = raw
    if answer is not None:
        raw = bytearray(records[word])
        if word in answer.positions:
            raw[6] = answer.positions[word]
        if word in answer.own:
            raw[15] = answer.own[word]
        view.players[word] = bytes(raw)
    expected = card(view, word, model.goaldat)
    if answer is not None:
        target = answer.marking.get(word, answer.live_marking.get(word))
        raw = view.players[word]
        if target is not None and raw[6] >= 2 and (word in answer.marking or not raw[16] & 0x40):
            from goal2.ui.squad_card import full_name
            expected['mark'] = full_name(model, target) if target else 'nobody'
    return expected


def _visible(test, widget, expected):
    test.assertEqual(widget.card, expected)
    test.assertEqual(widget.readiness.text(), expected['readiness'])
    test.assertEqual(widget.facts.values['performance'].text(), '*' * expected['performance_bar'])
    for field in ('age', 'caps', 'goals', 'height', 'foot'):
        test.assertEqual(widget.facts.values[field].text(), str(expected[field]))
    test.assertEqual(widget.positions.values['position'].text(), expected['position'])
    test.assertEqual(widget.positions.values['club position'].text(), expected['club_position'])
    test.assertEqual(widget.positions.values['cards'].text(), ', '.join(expected['cards']) or 'none')
    for name, word, fill, _ in expected['characteristics']:
        bar, label = widget.characteristics.rows[name]
        test.assertEqual(label.text(), word)
        test.assertEqual(bar.value, (fill, 14))
    for name, word, personal in expected['tactics']:
        test.assertEqual(widget.tactics.values[name].text(), word + (' P' if personal else ''))
    test.assertEqual(widget.tactics.values['mark'].text(), expected['mark'] or '—')


def verify_bench(test, screen, controller, receipts, phase):
    """Visit all20 actual S19 rows and a real S09 for each, without changing play."""
    from goal2.ui.s09_player_tactics import PlayerTacticsScreen
    answer = screen.answer
    data = controller.stop.data
    before = copy.deepcopy(answer.model.state)
    pairs = data['player_records']
    test.assertEqual([w for w, _ in pairs], answer.eleven + answer.bench)
    test.assertEqual(len(pairs), 20)
    test.assertEqual(len(answer.live_records), 20)
    original_row = screen.row
    visible = []
    changed_energy = changed_performance = 0
    for row, (word, encoded) in enumerate(pairs):
        raw = bytes.fromhex(encoded)
        test.assertEqual(answer.live_records[word], raw)
        test.assertEqual(answer._base_record(word), raw)
        expected = _expected(test, answer.model, data, word, answer)
        test.assertEqual(answer.card(word), expected)
        screen.row = row
        screen.refresh()
        _visible(test, screen.card, expected)
        personal = PlayerTacticsScreen(screen.window, answer.model, word, answer)
        try:
            test.assertEqual(personal.card(), expected)
            test.assertIn(expected['readiness'], personal.facts.text())
            for name, text, fill, _ in expected['characteristics']:
                bar, label = personal.characteristics.rows[name]
                test.assertEqual(label.text(), text)
                test.assertEqual(bar.value, (fill, 14))
            test.assertEqual(personal.lines()[:4], [(n, v + (' P' if own else '')) for n, v, own in expected['tactics']])
        finally:
            personal.deleteLater()
        initial = controller.given._snapshot.players[word]
        changed_energy += raw[14] != initial[14]
        changed_performance += raw[18:20] != initial[18:20]
        visible.append(expected)
    screen.row = original_row
    screen.refresh()
    test.assertEqual(len(screen.strip.shown_texts()), 20)
    test.assertEqual(answer.model.state, before, 'viewing every current card cannot mutate the career')
    receipts.append(dict(phase=phase, context=answer.context, records=20,
        records_sha256=_digest(pairs), visible_sha256=_digest(visible),
        changed_energy=changed_energy, changed_performance=changed_performance,
        all_records_and_rendered_fields_equal=True, career_unchanged=True))


def verify_choose(test, screen, model, data, receipts):
    pairs = data['player_records']
    test.assertEqual(len(pairs), 20)
    test.assertEqual([c['id'] for c in screen.cards], list(screen.words))
    for actual in screen.cards:
        test.assertEqual(actual, _expected(test, model, data, actual['id']))
    receipts.append(dict(phase='S16-' + screen.mode, records=20,
        records_sha256=_digest(pairs), visible_sha256=_digest(screen.cards), all_cards_equal=True))


def report(test, receipts, label):
    test.assertTrue(receipts)
    stops = [r for r in receipts if 'changed_energy' in r]
    test.assertTrue(stops)
    test.assertTrue(any(r['changed_energy'] for r in stops))
    test.assertTrue(any(r['changed_performance'] for r in stops))
    print('LIVE_CARDS_619 ' + json.dumps(dict(label=label, observations=receipts)), flush=True)
