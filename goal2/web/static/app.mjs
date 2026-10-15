// [designed: T35] Browser selections are drafts; the Python session owns country and roster data.
let session = null;
let countries = [];
let draft = { selected: new Set(), captain: null };
const $ = selector => document.querySelector(selector);
const rows = $('#squad-rows');

function safe(value) {
  return String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
}
function monogram(name) {
  const words = String(name || '?').trim().split(/\s+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : words[0]?.slice(0, 2) || '?').toUpperCase();
}
function chosenPlayers() { return session.players.filter(player => draft.selected.has(player.id)); }
function selectionMessage() {
  const count = draft.selected.size;
  if (count === 11) return 'Eleven selected; this remains a browser draft.';
  if (count < 11) return `Choose ${11 - count} more player${11 - count === 1 ? '' : 's'} to complete the draft.`;
  return `Remove ${count - 11} player${count - 11 === 1 ? '' : 's'} to complete the draft.`;
}
function resetDraft() {
  draft.selected = new Set(session.starting_eleven.slice(0, 11));
  draft.captain = session.captain && draft.selected.has(session.captain)
    ? session.captain : [...draft.selected][0] ?? null;
}
function showPage(name) {
  const isSquad = name === 'squad';
  $('#dashboard-page').classList.toggle('hidden', isSquad);
  $('#squad-page').classList.toggle('hidden', !isSquad);
  $('#topbar-page').textContent = isSquad ? 'Squad' : 'Overview';
  document.querySelectorAll('.nav-link').forEach(link => {
    const active = link.dataset.page === name;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
}
function paintCountryPicker() {
  $('#country-select').innerHTML = countries.map(country =>
    `<option value="${country.id}" ${country.id === session.country.id ? 'selected' : ''}>${safe(country.name)}</option>`
  ).join('');
  $('#country-select').disabled = false;
}
function render() {
  if (!session) return;
  const name = session.country.name;
  const badge = monogram(name);
  $('#club-country').textContent = name;
  $('#breadcrumb-country').textContent = name;
  $('#badge-country').textContent = name;
  $('#identity-country').textContent = name;
  $('#home-team').textContent = name;
  $('#country-monogram').textContent = badge;
  $('#club-monogram').textContent = badge;
  $('#team-monogram').textContent = badge;
  $('#home-monogram').textContent = badge;
  $('#large-monogram').textContent = badge;
  $('#dashboard-subheading').textContent = `${name} team at a glance.`;
  $('#squad-eyebrow').textContent = `${name.toLocaleUpperCase()} · TEAM MANAGEMENT`;
  $('#dashboard-roster-size').textContent = session.players.length;
  $('#roster-size').textContent = session.players.length;
  const matchup = session.matchup;
  if (matchup.available) {
    const opponent = matchup.opponent;
    $('#match-title').textContent = `${name} vs ${opponent.name}`;
    $('#away-team').textContent = opponent.name;
    $('#away-monogram').textContent = monogram(opponent.name);
    $('#home-side').textContent = matchup.managed_side === 0 ? 'TEAM A' : 'TEAM B';
    $('#away-side').textContent = matchup.managed_side === 0 ? 'TEAM B' : 'TEAM A';
    $('#match-status').textContent = 'Opponent identified';
  } else {
    $('#match-title').textContent = 'Matchup unavailable';
    $('#away-team').textContent = 'Unavailable';
    $('#away-monogram').textContent = '—';
    $('#home-side').textContent = 'YOUR TEAM';
    $('#away-side').textContent = 'OPPONENT';
    $('#match-status').textContent = 'This matchup is unavailable for the loaded game.';
  }
  paintCountryPicker();
  renderSquad();
}
function renderSquad(focusSelector = null) {
  if (!session) return;
  const selected = chosenPlayers();
  rows.innerHTML = session.players.map(player => {
    const isSelected = draft.selected.has(player.id);
    const captain = isSelected && player.id === draft.captain;
    return `<tr class="${isSelected ? 'is-selected' : ''}">
      <td class="select-col"><input class="player-check" type="checkbox" aria-label="Select ${safe(player.name)} for starting eleven draft" data-select="${player.id}" ${isSelected ? 'checked' : ''}></td>
      <td><div class="player-cell"><span class="player-number">${String(player.number).padStart(2, '0')}</span><span class="player-initials">${safe(player.initials)}</span><span class="player-name">${safe(player.name)}${captain ? '<span class="captain-mark" aria-label="Draft captain">C</span>' : ''}</span></div></td>
      <td><span class="position-cell"><span class="role-chip">${Number(player.position).toString(16).toUpperCase()}</span>code ${player.position}</span></td>
      <td><span class="rating-value">${player.ability}</span></td>
      <td><span class="energy-value">${player.energy}</span></td>
      <td class="captain-cell"><input type="radio" name="captain" aria-label="Make ${safe(player.name)} draft captain" data-captain="${player.id}" ${captain ? 'checked' : ''} ${isSelected ? '' : 'disabled'}></td>
    </tr>`;
  }).join('');
  const energy = selected.length ? Math.round(selected.reduce((sum, player) => sum + player.energy, 0) / selected.length) : '—';
  const captain = selected.find(player => player.id === draft.captain);
  $('#summary-xi').innerHTML = `${selected.length} <small>/ 11 selected</small>`;
  $('#summary-xi-note').textContent = selected.length === 11 ? 'Browser draft ready' : selectionMessage();
  $('#summary-captain').textContent = captain?.name ?? 'Not set';
  $('#summary-energy').textContent = energy;
  $('#selection-count').textContent = `${selected.length} of 11 selected`;
  $('#selection-guidance').textContent = selectionMessage();
  $('#squad-energy').textContent = energy;
  $('#selection-count').classList.toggle('complete', selected.length === 11);
  const captainSelect = $('#captain-select');
  captainSelect.disabled = selected.length === 0;
  captainSelect.innerHTML = selected.length
    ? selected.map(player => `<option value="${player.id}" ${player.id === draft.captain ? 'selected' : ''}>${safe(player.name)}</option>`).join('')
    : '<option value="" selected>No selected players</option>';
  if (focusSelector) $(focusSelector)?.focus({ preventScroll: true });
}
async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
async function chooseCountry(countryId) {
  const picker = $('#country-select');
  const previous = session.country.id;
  picker.disabled = true;
  try {
    session = await fetchJson('/api/country', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ country: Number(countryId) }),
    });
    if (session.country.id !== previous) resetDraft();
    $('#load-error').hidden = true;
    render();
  } catch (error) {
    picker.value = String(previous);
    $('#load-error').textContent = `Country change failed: ${error.message}`;
    $('#load-error').hidden = false;
  } finally {
    picker.disabled = false;
  }
}

document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => showPage('squad')));
$('.brand').addEventListener('click', event => { event.preventDefault(); showPage('dashboard'); });
$('#country-select').addEventListener('change', event => chooseCountry(event.target.value));
rows.addEventListener('change', event => {
  const selectId = Number(event.target.dataset.select);
  const captainId = Number(event.target.dataset.captain);
  if (event.target.dataset.select) {
    if (draft.selected.has(selectId)) {
      draft.selected.delete(selectId);
      if (draft.captain === selectId) draft.captain = [...draft.selected][0] ?? null;
    } else {
      draft.selected.add(selectId);
      if (!draft.captain) draft.captain = selectId;
    }
    renderSquad(`[data-select="${selectId}"]`);
  } else if (event.target.dataset.captain && draft.selected.has(captainId)) {
    draft.captain = captainId;
    renderSquad(`[data-captain="${captainId}"]`);
  }
});
$('#captain-select').addEventListener('change', event => {
  const id = Number(event.target.value);
  if (draft.selected.has(id)) { draft.captain = id; renderSquad('#captain-select'); }
});
$('#reset-button').addEventListener('click', () => { resetDraft(); renderSquad(); });

try {
  [countries, session] = await Promise.all([fetchJson('/api/countries').then(data => data.countries), fetchJson('/api/session')]);
  resetDraft();
  $('#load-error').hidden = true;
  render();
} catch (error) {
  $('#load-error').textContent = `Could not load the local game session: ${error.message}`;
  $('#load-error').hidden = false;
  $('#country-select').disabled = true;
}
