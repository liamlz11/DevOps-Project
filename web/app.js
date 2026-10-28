'use strict';
const $ = (id) => document.getElementById(id);
const clock = (value) => new Date(value).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
let queue = Promise.resolve();
let mutationPending = false;

async function api(path, options = {}) {
  const response = await fetch(path, {...options, signal: AbortSignal.timeout(7000)});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || 'Cannot reach the parking service. Please try again.');
  }
  return response.status === 204 ? null : response.json();
}

function textElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function render(data) {
  $('count').textContent = data.count;
  $('capacity').textContent = ` / ${data.capacity} spaces`;
  $('available').textContent = Math.max(0, data.capacity - data.count);
  $('gate').textContent = data.full ? 'Lot full · entry paused' : 'Open for arrivals';
  $('gate').classList.toggle('full', data.full);
  $('vehicle-total').textContent = `${data.count} ${data.count === 1 ? 'vehicle' : 'vehicles'}`;
  $('vehicles').replaceChildren();
  $('empty').hidden = data.count !== 0;
  $('empty').textContent = 'The lot is clear. Register an arrival to get started.';
  for (const vehicle of data.vehicles) {
    const row = document.createElement('tr');
    row.append(textElement('td', vehicle.plate, 'plate'));
    const timeCell = document.createElement('td');
    const time = textElement('time', clock(vehicle.entered_at));
    time.dateTime = vehicle.entered_at;
    time.title = new Date(vehicle.entered_at).toLocaleString();
    timeCell.append(time);
    const action = document.createElement('td');
    const button = textElement('button', 'Release', 'release');
    button.setAttribute('aria-label', `Release ${vehicle.plate}`);
    button.disabled = mutationPending;
    button.addEventListener('click', () => mutate(() => api(`/api/vehicles/${encodeURIComponent(vehicle.plate)}`, {method:'DELETE'}), `${vehicle.plate} released. Space available.`));
    action.append(button);
    row.append(timeCell, action);
    $('vehicles').append(row);
  }
  $('bays').replaceChildren();
  for (let index = 0; index < Math.min(data.capacity, 20); index++) {
    const taken = index < data.count;
    const bay = textElement('div', '', `bay${taken ? ' taken' : ''}`);
    // Static SVG only. API values are always inserted as text nodes.
    if (taken) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox','0 0 40 26');
      svg.setAttribute('aria-hidden','true');
      const path = document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d','M5 18v-7l4-7h22l4 7v7M5 11h30M9 18h22M9 18v4H5v-4m26 0v4h4v-4M9 14h5m12 0h5');
      svg.append(path); bay.append(svg);
    }
    bay.append(textElement('span', `${String(index + 1).padStart(2, '0')} · ${taken ? 'Parked' : 'Free'}`));
    $('bays').append(bay);
  }
  if (data.capacity > 20) $('bays').append(textElement('p', `${data.capacity - 20} more spaces tracked in the totals.`));
  $('history').replaceChildren();
  $('history-empty').hidden = data.recent_entries.length !== 0;
  for (const entry of data.recent_entries) {
    const item = document.createElement('li');
    const time = textElement('time', clock(entry.entered_at));
    time.dateTime = entry.entered_at;
    time.title = new Date(entry.entered_at).toLocaleString();
    item.append(textElement('span', entry.plate, 'plate'), time);
    $('history').append(item);
  }
}

function refresh() {
  // Polls and action-triggered refreshes share one queue: responses cannot race.
  queue = queue.catch(() => {}).then(async () => {
    try {
      render(await api('/api/parking'));
      $('outage').hidden = true;
      $('connection').textContent = 'Live';
      $('connection').className = 'connection online';
      $('updated').textContent = `Updated ${clock(new Date())}`;
    } catch (error) {
      $('outage').hidden = false;
      $('connection').textContent = 'Reconnecting';
      $('connection').className = 'connection offline';
      $('updated').textContent = 'Showing last received data';
    }
  });
  return queue;
}

async function mutate(operation, success) {
  if (mutationPending) return;
  mutationPending = true;
  document.querySelectorAll('button').forEach(button => {button.disabled = true;});
  $('message').textContent = '';
  try {
    await operation();
    $('message').className = 'message success';
    $('message').textContent = success;
  } catch (error) {
    $('message').className = 'message error';
    $('message').textContent = error.message;
  } finally {
    mutationPending = false;
    await refresh();
    document.querySelectorAll('button').forEach(button => {button.disabled = false;});
  }
}

$('entry-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const plate = $('plate').value.trim().toUpperCase();
  mutate(async () => {
    await api('/api/entries', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({plate})});
    $('plate').value = '';
  }, `${plate} admitted. Welcome to Gatehouse.`);
});

(async function poll() { await refresh(); setTimeout(poll, 2000); })();
