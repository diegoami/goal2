// [designed: T35, T37] Browser selections are drafts; the Python session owns country, roster and friendly actions.
let session = null;
let countries = [];
let draft = { selected: new Set(), captain: null, tactics: 0 };
let busy = false;
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
// [derived: F027; designed: T44] A complete draft still needs available starters.
function selectionMessage() {
  const unavailable = chosenPlayers().filter(player => player.availability && !player.availability.available);
  if (unavailable.length) return `Replace unavailable players: ${unavailable.map(player => player.name).join(", ")}.`;
  const count = draft.selected.size;
  if (count === 11) return 'Eleven selected; this remains a browser draft.';
  if (count < 11) return `Choose ${11 - count} more player${11 - count === 1 ? '' : 's'} to complete the draft.`;
  return `Remove ${count - 11} player${count - 11 === 1 ? '' : 's'} to complete the draft.`;
}
function tacticsMessage(value) {
  return session.tactics_options.map(option => {
    const set = Boolean(value & (1 << (option.element - 1)));
    return `${set ? option.set : option.clear} (element ${option.element})`;
  }).join(' · ');
}
function resetDraft() {
  draft.selected = new Set(session.confirmed.starting_eleven);
  draft.captain = session.confirmed.captain && draft.selected.has(session.confirmed.captain)
    ? session.confirmed.captain : [...draft.selected][0] ?? null;
  draft.tactics = session.confirmed.tactics;
}
function setBusy(value) {
  busy = value;
  $('#country-select').disabled = value || Boolean(session?.campaign);
  $('#new-campaign-button').disabled = value;
  document.querySelectorAll('#campaign-form input, #campaign-form select').forEach(control => { control.disabled = value; });
  $('#confirm-button').disabled = value || !draftIsValid();
  $('#play-button').disabled = value || !session?.matchup.available;
  $('#another-button').disabled = value;
  $('#cancel-button').disabled = value;
  $('#reset-button').disabled = value;
  $('#save-session-button').disabled = value;
  $('#load-session-button').disabled = value;
  if (value) document.querySelectorAll('.player-check, [data-captain], #captain-select, [data-tactic-bit]').forEach(control => { control.disabled = true; });
}
function draftIsValid() { return draft.selected.size === 11 && draft.selected.has(draft.captain) && chosenPlayers().every(player => !player.availability || player.availability.available); }
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
  $('#country-select').disabled = busy || Boolean(session.campaign);
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
    $('#match-status').textContent = 'Ready for an explicit Play action';
  } else {
    $('#match-title').textContent = 'Matchup unavailable';
    $('#away-team').textContent = 'Unavailable';
    $('#away-monogram').textContent = '—';
    $('#home-side').textContent = 'YOUR TEAM';
    $('#away-side').textContent = 'OPPONENT';
    $('#match-status').textContent = 'This matchup is unavailable for the loaded game.';
  }
  const lastMatch = session.last_match;
  $('#match-result').hidden = !lastMatch;
  $('#another-button').hidden = !lastMatch;
  $('#match-eyebrow').textContent = lastMatch ? 'COMPLETED FRIENDLY' : 'FRIENDLY MATCHUP';
  $('#match-tag').textContent = lastMatch ? `MATCH ${lastMatch.match_count}` : 'READY';
  $('#match-feedback').textContent = lastMatch ? 'Result retained in this session.' : 'No match has been simulated';
  if (lastMatch) {
    const managed = lastMatch.teams[lastMatch.managed_side];
    const firstTeam = lastMatch.teams[0];
    const secondTeam = lastMatch.teams[1];
    $('#match-title').textContent = `${firstTeam.name} vs ${secondTeam.name}`;
    $('#home-team').textContent = firstTeam.name;
    $('#away-team').textContent = secondTeam.name;
    $('#home-side').textContent = lastMatch.managed_side === 0 ? 'MANAGED TEAM · TEAM A' : 'TEAM A';
    $('#away-side').textContent = lastMatch.managed_side === 1 ? 'MANAGED TEAM · TEAM B' : 'TEAM B';
    $('#home-monogram').textContent = monogram(firstTeam.name);
    $('#away-monogram').textContent = monogram(secondTeam.name);
    $('#score-caption').textContent = 'FULL TIME';
    $('#match-score').textContent = `${lastMatch.score[0]} – ${lastMatch.score[1]}`;
    $('#match-status').textContent = `Half-time ${lastMatch.halftime_scores[0].join('–')} · full-time ${lastMatch.halftime_scores[1].join('–')}`;
    $('#result-heading').textContent = `Managed side: ${managed.name} · ${firstTeam.name} ${lastMatch.score[0]}–${lastMatch.score[1]} ${secondTeam.name}`;
    $('#goal-events').innerHTML = lastMatch.goals.length
      ? lastMatch.goals.map(goal => `<li>${goal.minute}' · ${safe(goal.player_name)} · ${safe(goal.team_name)}</li>`).join('')
      : '<li>No goals</li>';
    $('#result-detail').textContent = `Match ${lastMatch.match_count} · half-time ${lastMatch.halftime_scores[0].join('–')} · seeds ${lastMatch.seeds.join(' / ')}`;
  } else {
    $('#score-caption').textContent = 'EXPLICIT PLAY REQUIRED';
    $('#match-score').textContent = 'VS';
    $('#goal-events').replaceChildren();
    $('#result-detail').textContent = '';
  }
  $('#play-button').disabled = busy || !session.matchup.available;
  $('#play-button').textContent = session.campaign ? 'Play scheduled friendly' : lastMatch ? 'Play another friendly' : 'Play friendly';
  $('#campaign-status').hidden = !session.campaign;
  if (!$('#campaign-country').options.length) {
    $('#campaign-country').innerHTML = countries.map(country =>
      `<option value="${country.id}" ${country.id === session.country.id ? 'selected' : ''}>${safe(country.name)}</option>`
    ).join('');
  }
  if (session.campaign) {
    const campaign = session.campaign;
    $('#campaign-stage').textContent = `Campaign ${campaign.start_year} · cycle ${campaign.cycle} · year ${campaign.year} · stage ${campaign.stage}`;
    const fixture = campaign.next_fixture;
    $('#campaign-next').textContent = fixture
      ? `Next: ${fixture.teams[0].name} (team A) vs ${fixture.teams[1].name} (team B) · ${fixture.kind === 1 ? 'Friendly' : `Competitive kind ${fixture.kind}`} · stage ${fixture.stage} · ${fixture.fixture_id}`
      : 'No next fixture is supplied.';
    $('#campaign-boundary').textContent = matchup.available ? 'Only Play scheduled friendly advances the schedule.' : matchup.message;
    $('#campaign-history').innerHTML = campaign.history.map(row =>
      `<li>${safe(row.fixture_id)} · ${safe(row.teams[0].name)} ${row.score.join('–')} ${safe(row.teams[1].name)}</li>`
    ).join('');
  }
  paintCountryPicker();
  const confirmedPlayers = session.players.filter(player => session.confirmed.starting_eleven.includes(player.id));
  $('#team-morale').textContent = session.team_morale;
  $('#result-morale').textContent = session.team_morale;
  $('#confirmed-eleven').textContent = confirmedPlayers.map(player => player.name).join(', ') || 'Not set';
  $('#confirmed-captain').textContent = session.players.find(player => player.id === session.confirmed.captain)?.name ?? 'Not set';
  $('#confirmed-tactics').textContent = tacticsMessage(session.confirmed.tactics);
  renderTactics();
  renderSquad();
}
function renderTactics(focusBit = null) {
  $('#tactics-controls').innerHTML = session.tactics_options.map(option => {
    const bit = option.element - 1;
    const selected = Boolean(draft.tactics & (1 << bit));
    const clear = safe(option.clear);
    const set = safe(option.set);
    const label = selected ? set : clear;
    const evidence = option.evidence === 'confirmed' ? 'F010 confirmed label' : 'Rebuild label';
    return `<label class="tactic-option"><input type="checkbox" data-tactic-bit="${bit}" aria-label="Element ${option.element}: ${clear} or ${set}" ${selected ? 'checked' : ''} ${busy ? 'disabled' : ''}><span><strong>${label}</strong><small>Element ${option.element} · ${evidence}</small></span></label>`;
  }).join('');
  if (focusBit !== null) $(`[data-tactic-bit="${focusBit}"]`)?.focus({ preventScroll: true });
}
function renderSquad(focusSelector = null) {
  if (!session) return;
  const selected = chosenPlayers();
  rows.innerHTML = session.players.map(player => {
    const isSelected = draft.selected.has(player.id);
    const captain = isSelected && player.id === draft.captain;
    return `<tr class="${isSelected ? 'is-selected' : ''}">
      <td class="select-col"><input class="player-check" type="checkbox" aria-label="Select ${safe(player.name)} for starting eleven draft" data-select="${player.id}" ${isSelected ? 'checked' : ''} ${busy || (player.availability && !player.availability.available && !isSelected) ? 'disabled' : ''}></td>
      <td><div class="player-cell"><span class="player-number">${String(player.number).padStart(2, '0')}</span><span class="player-initials">${safe(player.initials)}</span><span class="player-name">${safe(player.name)}${player.availability && !player.availability.available ? `<small class="availability-reason">${safe(player.availability.reasons.join(", "))}</small>` : player.availability?.carried_bookings ? '<small class="availability-reason">1 booking carried</small>' : ""}${captain ? '<span class="captain-mark" aria-label="Draft captain">C</span>' : ''}</span></div></td>
      <td><span class="position-cell"><span class="role-chip">${Number(player.position).toString(16).toUpperCase()}</span>code ${player.position}</span></td>
      <td><span class="rating-value">${player.ability}</span></td>
      <td><span class="energy-value">${player.energy}</span></td>
      <td><span class="confidence-value">${player.confidence}</span></td>
      <td class="captain-cell"><input type="radio" name="captain" aria-label="Make ${safe(player.name)} draft captain" data-captain="${player.id}" ${captain ? 'checked' : ''} ${isSelected && !busy ? '' : 'disabled'}></td>
    </tr>`;
  }).join('');
  const energy = selected.length ? Math.round(selected.reduce((sum, player) => sum + player.energy, 0) / selected.length) : '—';
  const captain = selected.find(player => player.id === draft.captain);
  $('#summary-xi').innerHTML = `${selected.length} <small>/ 11 selected</small>`;
  $('#summary-xi-note').textContent = draftIsValid() ? 'Browser draft ready' : selectionMessage();
  $('#summary-captain').textContent = captain?.name ?? 'Not set';
  $('#summary-energy').textContent = energy;
  $('#selection-count').textContent = `${selected.length} of 11 selected`;
  $('#selection-guidance').textContent = selectionMessage();
  $('#squad-energy').textContent = energy;
  $('#selection-count').classList.toggle('complete', draftIsValid());
  const captainSelect = $('#captain-select');
  captainSelect.disabled = selected.length === 0 || busy;
  captainSelect.innerHTML = selected.length
    ? selected.map(player => `<option value="${player.id}" ${player.id === draft.captain ? 'selected' : ''}>${safe(player.name)}</option>`).join('')
    : '<option value="" selected>No selected players</option>';
  $('#confirm-button').disabled = busy || !draftIsValid();
  $('#play-button').disabled = busy || !session.matchup.available;
  $('#management-feedback').textContent = draftIsValid()
    ? 'Draft valid. Confirm to update the local game session, or cancel to restore confirmed choices.'
    : selectionMessage() + (draft.selected.has(draft.captain) ? '' : ' Choose a captain from the eleven.');
  if (focusSelector) $(focusSelector)?.focus({ preventScroll: true });
}
async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.data = data;
    throw error;
  }
  return data;
}
async function chooseCountry(countryId) {
  const picker = $('#country-select');
  const previous = session.country.id;
  setBusy(true);
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
    setBusy(false);
    renderTactics();
    renderSquad();
  }
}
async function confirmDraft() {
  setBusy(true);
  $('#management-feedback').textContent = 'Confirming team choices…';
  let confirmed = false;
  let failure = null;
  try {
    session = await fetchJson('/api/management', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        country: session.country.id,
        starting_eleven: session.players.filter(player => draft.selected.has(player.id)).map(player => player.id),
        captain: draft.captain,
        tactics: draft.tactics,
      }),
    });
    resetDraft();
    render();
    confirmed = true;
  } catch (error) {
    failure = `Team was not confirmed: ${error.message}`;
  } finally {
    setBusy(false);
    renderTactics();
    renderSquad();
    if (confirmed) $('#management-feedback').textContent = 'Team confirmed in the local game session.';
    if (failure) $('#management-feedback').textContent = failure;
  }
}
async function playFriendly() {
  if (busy || !session?.matchup.available) return;
  setBusy(true);
  $('#match-feedback').textContent = 'Playing friendly…';
  try {
    session = await fetchJson('/api/play', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ play_token: session.play_token,
        ...(session.campaign ? { fixture_id: session.campaign.next_fixture.fixture_id } : {}),
      }),
    });
    render();
  } catch (error) {
    if (error.data?.play_token) session.play_token = error.data.play_token;
    $('#match-feedback').textContent = `Friendly failed: ${error.message}`;
  } finally {
    setBusy(false);
    renderTactics();
    renderSquad();
  }
}

async function saveSession() {
  setBusy(true);
  $('#save-feedback').textContent = 'Saving session…';
  try {
    await fetchJson('/api/save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    $('#save-feedback').textContent = 'Session saved. Copy the .g2save file to move it to another computer.';
  } catch (error) {
    $('#save-feedback').textContent = `Save failed: ${error.message}`;
  } finally {
    setBusy(false);
    renderTactics();
    renderSquad();
  }
}
async function loadSession() {
  setBusy(true);
  $('#save-feedback').textContent = 'Checking saved session…';
  try {
    session = await fetchJson('/api/load', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    resetDraft();
    showPage('dashboard');
    render();
    $('#save-feedback').textContent = 'Saved session loaded. No match was simulated.';
  } catch (error) {
    $('#save-feedback').textContent = `Load failed; current session is unchanged: ${error.message}`;
  } finally {
    setBusy(false);
    renderTactics();
    renderSquad();
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
$('#reset-button').addEventListener('click', () => { resetDraft(); renderTactics(); renderSquad(); });
$('#cancel-button').addEventListener('click', () => {
  resetDraft();
  renderTactics();
  renderSquad();
  $('#management-feedback').textContent = 'Draft canceled. Confirmed team choices restored.';
});
$('#confirm-button').addEventListener('click', confirmDraft);
$('#play-button').addEventListener('click', playFriendly);
$('#campaign-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  setBusy(true);
  try {
    session = await fetchJson('/api/campaign', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ country: Number($('#campaign-country').value),
        start_year: Number($('#campaign-year').value), seed_7b62: Number($('#campaign-seed').value),
        seed_8336: Number($('#campaign-seed2').value) }),
    });
    resetDraft();
    render();
    $('#campaign-feedback').textContent = 'New campaign started. Manage your team, then play the scheduled friendly.';
  } catch (error) {
    $('#campaign-feedback').textContent = `Campaign was not started: ${error.message}`;
  } finally {
    setBusy(false);
    renderTactics();
    renderSquad();
  }
});
$('#save-session-button').addEventListener('click', saveSession);
$('#load-session-button').addEventListener('click', loadSession);
$('#tactics-controls').addEventListener('change', event => {
  if (event.target.dataset.tacticBit === undefined) return;
  const bit = Number(event.target.dataset.tacticBit);
  draft.tactics = event.target.checked ? draft.tactics | (1 << bit) : draft.tactics & ~(1 << bit);
  renderTactics(bit);
  $('#management-feedback').textContent = 'Tactics draft changed. Confirm to update the local game session.';
});

try {
  [countries, session] = await Promise.all([fetchJson('/api/countries').then(data => data.countries), fetchJson('/api/session')]);
  resetDraft();
  $('#load-error').hidden = true;
  render();
  setBusy(false); // [designed: T41] Reload enables Save/Load without requiring a country change.
} catch (error) {
  $('#load-error').textContent = `Could not load the local game session: ${error.message}`;
  $('#load-error').hidden = false;
  $('#country-select').disabled = true;
}
