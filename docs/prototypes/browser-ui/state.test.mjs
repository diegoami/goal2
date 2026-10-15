import test from 'node:test';
import assert from 'node:assert/strict';
import { createSampleState, resetSampleState, selectedPlayers, selectionMessage, toggleSelection, setCaptain, selectedEnergy } from './state.mjs';

test('sample state starts with an eleven and an eligible captain', () => {
  const state = createSampleState();
  assert.equal(selectedPlayers(state).length, 11);
  assert.ok(selectedPlayers(state).some(player => player.id === state.captainId));
  assert.equal(selectedEnergy(state), 22);
});

test('selection feedback describes counts above and below eleven', () => {
  const state = createSampleState();
  assert.equal(toggleSelection(state, 'krogh').changed, true);
  assert.equal(selectedPlayers(state).length, 12);
  assert.match(selectionMessage(state), /1 fewer player/);
  assert.equal(toggleSelection(state, 'krogh').changed, true);
  assert.equal(selectedPlayers(state).length, 11);
  toggleSelection(state, 'madsen');
  assert.match(selectionMessage(state), /Choose 1 more player/);
});

test('removing the captain synchronizes leadership to a remaining selected player', () => {
  const state = createSampleState();
  const oldCaptain = state.captainId;
  assert.equal(toggleSelection(state, oldCaptain).changed, true);
  assert.notEqual(state.captainId, oldCaptain);
  assert.ok(selectedPlayers(state).some(player => player.id === state.captainId));
});

test('captain changes are limited to selected players', () => {
  const state = createSampleState();
  assert.equal(setCaptain(state, 'bro'), true);
  assert.equal(state.captainId, 'bro');
  assert.equal(setCaptain(state, 'krogh'), false);
  assert.equal(state.captainId, 'bro');
});

test('reset returns a fresh copy of the sample selection and captain', () => {
  const state = createSampleState();
  toggleSelection(state, 'madsen');
  setCaptain(state, 'bro');
  const reset = resetSampleState();
  assert.equal(selectedPlayers(reset).length, 11);
  assert.equal(reset.captainId, 'skov');
  assert.ok(selectedPlayers(reset).some(player => player.id === reset.captainId));
  assert.notEqual(reset.players, state.players);
});

test('empty selection has no captain and selecting a player restores an eligible captain', () => {
  const state = createSampleState();
  for (const player of selectedPlayers(state).slice()) toggleSelection(state, player.id);
  assert.equal(selectedPlayers(state).length, 0);
  assert.equal(state.captainId, null);
  assert.match(selectionMessage(state), /Choose 11 more players/);
  assert.equal(setCaptain(state, 'krogh'), false);
  toggleSelection(state, 'krogh');
  assert.equal(state.captainId, 'krogh');
  assert.equal(selectedPlayers(state).some(player => player.id === state.captainId), true);
});
