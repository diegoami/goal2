// [designed] Browser-only interaction layer for the sample preview.
import { createSampleState, resetSampleState, selectedPlayers, selectedEnergy, selectionMessage, toggleSelection, setCaptain } from './state.mjs';

let state = createSampleState();
const dashboard = document.querySelector('#dashboard-page');
const squad = document.querySelector('#squad-page');
const rows = document.querySelector('#squad-rows');
const captainSelect = document.querySelector('#captain-select');

function showPage(name) {
  const isSquad = name === 'squad';
  dashboard.classList.toggle('hidden', isSquad);
  squad.classList.toggle('hidden', !isSquad);
  document.querySelector('#topbar-page').textContent = isSquad ? 'Squad' : 'Overview';
  document.querySelectorAll('.nav-link').forEach(link => {
    const active = link.dataset.page === name;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
}

function updateSummary() {
  const chosen = selectedPlayers(state);
  const count = chosen.length;
  const captain = chosen.find(player => player.id === state.captainId);
  document.querySelector('#summary-xi').innerHTML = `${count} <small>/ 11 selected</small>`;
  document.querySelector('#summary-xi-note').textContent = count === 11 ? 'Ready to review' : selectionMessage(state);
  document.querySelector('#summary-captain').textContent = captain?.name ?? 'Not set';
  document.querySelector('#summary-energy').innerHTML = `${selectedEnergy(state)}<small> / 25</small>`;
  document.querySelector('#selection-count').textContent = `${count} of 11 selected`;
  document.querySelector('#selection-guidance').textContent = selectionMessage(state);
  document.querySelector('#squad-energy').textContent = `${selectedEnergy(state)} / 25`;
  document.querySelector('#selection-count').classList.toggle('complete', count === 11);
}

function renderSquad(focusSelector = null) {
  const chosen = selectedPlayers(state);
  document.querySelector('#roster-size').textContent = state.players.length;
  rows.innerHTML = state.players.map(player => {
    const captain = player.id === state.captainId && player.selected;
    return `<tr class="${player.selected ? 'is-selected' : ''}">
      <td class="select-col"><input class="player-check" type="checkbox" aria-label="Select ${player.name} for starting eleven" data-select="${player.id}" ${player.selected ? 'checked' : ''}></td>
      <td><div class="player-cell"><span class="player-number">${String(player.number).padStart(2, '0')}</span><span class="player-name">${player.name}${captain ? '<span class="captain-mark" aria-label="Captain">C</span>' : ''}</span></div></td>
      <td><span class="position-cell"><span class="role-chip role-${player.role.toLowerCase()}">${player.role}</span>${player.position}</span></td>
      <td><span class="rating-value">${player.ability}</span><span class="rating-track"><i style="width:${player.ability}%"></i></span></td>
      <td><span class="energy-value ${player.energy < 20 ? 'energy-low' : ''}">${player.energy}</span><span class="energy-track"><i style="width:${player.energy / 25 * 100}%"></i></span></td>
      <td class="captain-cell"><input type="radio" name="captain" aria-label="Make ${player.name} captain" data-captain="${player.id}" ${captain ? 'checked' : ''} ${player.selected ? '' : 'disabled'}></td>
    </tr>`;
  }).join('');
  captainSelect.disabled = chosen.length === 0;
  captainSelect.innerHTML = chosen.length
    ? chosen.map(player => `<option value="${player.id}" ${player.id === state.captainId ? 'selected' : ''}>${player.name}</option>`).join('')
    : '<option value="" selected>No selected players</option>';
  updateSummary();
  // [designed] Keep keyboard users on the control whose in-memory change triggered this render.
  if (focusSelector) document.querySelector(focusSelector)?.focus({ preventScroll: true });
}

document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.go)));
document.querySelector('.brand').addEventListener('click', event => {
  event.preventDefault();
  showPage('dashboard');
});
rows.addEventListener('change', event => {
  const selectId = event.target.dataset.select;
  const captainId = event.target.dataset.captain;
  if (selectId) {
    const result = toggleSelection(state, selectId);
    if (!result.changed) event.target.checked = !event.target.checked;
    renderSquad(`[data-select="${selectId}"]`);
  }
  if (captainId && setCaptain(state, captainId)) renderSquad(`[data-captain="${captainId}"]`);
});
captainSelect.addEventListener('change', event => {
  if (setCaptain(state, event.target.value)) renderSquad('#captain-select');
});
document.querySelector('#reset-button').addEventListener('click', () => {
  state = resetSampleState();
  renderSquad();
});
renderSquad();
