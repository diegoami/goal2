// [designed] Fictional roster and selection rules for the browser interface preview.
export const samplePlayers = Object.freeze([
  { id: 'madsen', name: 'Mikkel Madsen', number: 1, position: 'Goalkeeper', role: 'GK', ability: 84, energy: 22, selected: true },
  { id: 'lund', name: 'Jonas Lund', number: 2, position: 'Right back', role: 'DF', ability: 79, energy: 21, selected: true },
  { id: 'holm', name: 'Anders Holm', number: 3, position: 'Centre back', role: 'DF', ability: 82, energy: 23, selected: true },
  { id: 'vester', name: 'Emil Vester', number: 4, position: 'Centre back', role: 'DF', ability: 80, energy: 22, selected: true },
  { id: 'borg', name: 'Kasper Borg', number: 5, position: 'Left back', role: 'DF', ability: 78, energy: 21, selected: true },
  { id: 'nielsen', name: 'Frederik Nielsen', number: 6, position: 'Defensive mid', role: 'MF', ability: 83, energy: 22, selected: true },
  { id: 'skov', name: 'Lasse Skov', number: 7, position: 'Central mid', role: 'MF', ability: 85, energy: 23, selected: true },
  { id: 'gaard', name: 'Oliver Gaard', number: 8, position: 'Central mid', role: 'MF', ability: 81, energy: 21, selected: true },
  { id: 'bro', name: 'Mathias Bro', number: 9, position: 'Right wing', role: 'FW', ability: 86, energy: 22, selected: true },
  { id: 'eriksen', name: 'Nikolaj Eriksen', number: 10, position: 'Striker', role: 'FW', ability: 88, energy: 24, selected: true },
  { id: 'nygaard', name: 'Anton Nygaard', number: 11, position: 'Left wing', role: 'FW', ability: 84, energy: 20, selected: true },
  { id: 'krogh', name: 'Tobias Krogh', number: 12, position: 'Goalkeeper', role: 'GK', ability: 76, energy: 25, selected: false },
  { id: 'falk', name: 'Simon Falk', number: 13, position: 'Centre back', role: 'DF', ability: 77, energy: 23, selected: false },
  { id: 'dahl', name: 'Rasmus Dahl', number: 14, position: 'Right back', role: 'DF', ability: 75, energy: 24, selected: false },
  { id: 'moller', name: 'Victor Moller', number: 15, position: 'Central mid', role: 'MF', ability: 79, energy: 24, selected: false },
  { id: 'poulsen', name: 'Noah Poulsen', number: 16, position: 'Attacking mid', role: 'MF', ability: 82, energy: 23, selected: false },
  { id: 'beck', name: 'Daniel Beck', number: 17, position: 'Left wing', role: 'FW', ability: 78, energy: 22, selected: false },
  { id: 'kristensen', name: 'Elias Kristensen', number: 18, position: 'Striker', role: 'FW', ability: 80, energy: 24, selected: false },
  { id: 'pedersen', name: 'Mads Pedersen', number: 19, position: 'Central mid', role: 'MF', ability: 77, energy: 21, selected: false },
  { id: 'sorensen', name: 'Frederik Sorensen', number: 20, position: 'Right wing', role: 'FW', ability: 79, energy: 25, selected: false },
]);

export function createSampleState() {
  return { players: samplePlayers.map(player => ({ ...player })), captainId: 'skov' };
}

export function selectedPlayers(state) {
  return state.players.filter(player => player.selected);
}

export function selectionMessage(state) {
  const count = selectedPlayers(state).length;
  if (count === 11) return 'Your starting eleven is ready.';
  if (count < 11) return `Choose ${11 - count} more player${11 - count === 1 ? '' : 's'} to complete your starting eleven.`;
  return `Choose ${count - 11} fewer player${count - 11 === 1 ? '' : 's'} for a starting eleven.`;
}

export function toggleSelection(state, playerId) {
  const player = state.players.find(item => item.id === playerId);
  if (!player) return { state, changed: false, reason: 'unknown-player' };
  player.selected = !player.selected;
  if (!player.selected && state.captainId === playerId) {
    state.captainId = selectedPlayers(state)[0]?.id ?? null;
  }
  if (player.selected && !state.captainId) state.captainId = playerId;
  return { state, changed: true, reason: null };
}

export function setCaptain(state, playerId) {
  const player = state.players.find(item => item.id === playerId && item.selected);
  if (!player) return false;
  state.captainId = player.id;
  return true;
}

export function resetSampleState() {
  return createSampleState();
}

export function selectedEnergy(state) {
  const players = selectedPlayers(state);
  return players.length ? Math.round(players.reduce((sum, player) => sum + player.energy, 0) / players.length) : 0;
}
