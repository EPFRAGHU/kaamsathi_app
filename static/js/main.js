// Availability switch (home screen)
let isOn = false;
function toggleAvail(){
  isOn = !isOn;
  const card = document.getElementById('availCard');
  if(!card) return;
  const sw = document.getElementById('availSwitch');
  const sub = document.getElementById('availSub');
  const status = document.getElementById('availStatus');
  const num = document.getElementById('meterNum');
  if(isOn){
    card.classList.add('on');
    sw.classList.add('on');
    sub.textContent = "You're visible to employers nearby";
    status.textContent = 'ON · matching you with jobs now';
    num.textContent = '₹2,650';
  } else {
    card.classList.remove('on');
    sw.classList.remove('on');
    sub.textContent = 'Turn on to get matched with jobs nearby';
    status.textContent = 'OFF · not receiving job alerts';
    num.textContent = '₹0';
  }
}

// Role toggle (register page) — shows worker fields or employer fields
function selectRole(el, role){
  const grid = document.getElementById('roleGrid');
  if(grid){
    grid.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    el.querySelector('input').checked = true;
  }
  const workerFields = document.getElementById('workerFields');
  const employerFields = document.getElementById('employerFields');
  if(workerFields && employerFields){
    workerFields.style.display = role === 'worker' ? 'block' : 'none';
    employerFields.style.display = role === 'employer' ? 'block' : 'none';
  }
}

// Category chip selection (post-a-job screen)
function selectChip(el){
  const grid = document.getElementById('chipGrid');
  if(!grid) return;
  grid.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  el.querySelector('input').checked = true;
  const err = document.getElementById('categoryError');
  if(err) err.style.display = 'none';
}
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('chipGrid');
  if(grid){
    const first = grid.querySelector('.chip');
    if(first) first.classList.add('selected');
  }
});

// Worker count stepper (post-a-job screen)
function stepWorkers(delta){
  const span = document.getElementById('workerCount');
  const input = document.getElementById('workersInput');
  if(!span || !input) return;
  let val = parseInt(span.textContent, 10) + delta;
  if(val < 1) val = 1;
  if(val > 50) val = 50;
  span.textContent = val;
  input.value = val;
}

// Post-a-job form validation
function validateJobForm(){
  let valid = true;
  const wage = document.getElementById('wageInput');
  const wageError = document.getElementById('wageError');
  if(wage && (!wage.value || Number(wage.value) <= 0)){
    wageError.style.display = 'block';
    valid = false;
  } else if(wageError){
    wageError.style.display = 'none';
  }

  const location = document.getElementById('locationInput');
  const locationError = document.getElementById('locationError');
  if(location && !location.value.trim()){
    locationError.style.display = 'block';
    valid = false;
  } else if(locationError){
    locationError.style.display = 'none';
  }

  return valid;
}
