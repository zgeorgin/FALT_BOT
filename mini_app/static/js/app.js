const API_URL = '/api';
let token = localStorage.getItem('falt_token');
let user = JSON.parse(localStorage.getItem('falt_user') || 'null');
let selectedMachine = null;
let selectedTime = null;
let selectedDate = null;

let tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

// Проверка при загрузке
document.addEventListener('DOMContentLoaded', function() {
    if (token && user) {
        validateSession();
    } else {
        showPage('login');
    }
});

async function validateSession() {
    try {
        var data = await apiGet('/wallet/balance');
        user.wallet = data.balance;
        localStorage.setItem('falt_user', JSON.stringify(user));
        updateHeaderBalance();
        updateProfile();
        
        showPage('home-step1');
        loadMachines();
    } catch(e) {
        console.error('Session invalid:', e);
        logout();
    }
}

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(function(p) {
        p.classList.remove('active');
    });
    var target = document.getElementById(pageId);
    if (target) target.classList.add('active');

    if (pageId === 'profile') {
        updateProfile();
    }
    
    document.querySelectorAll('.nav-btn').forEach(function(btn, idx) {
        btn.classList.remove('active');
        if (pageId.startsWith('home') && idx === 0) btn.classList.add('active');
        if (pageId === 'bookings' && idx === 1) btn.classList.add('active');
        if (pageId === 'studyroom' && idx === 2) btn.classList.add('active');
        if ((pageId === 'profile' || pageId === 'topup-placeholder') && idx === 3) btn.classList.add('active');
    });

    if (pageId === 'home-step1' && token) {
        apiGet('/wallet/balance').then(function(data) {
            user.wallet = data.balance;
            localStorage.setItem('falt_user', JSON.stringify(user));
            updateHeaderBalance();
        });
    }
}

// ВХОД — глобальная функция
function handleLogin() {
    var emailInput = document.getElementById('email-input');
    if (!emailInput) {
        alert('Поле email не найдено');
        return;
    }
    
    var email = emailInput.value.trim();
    if (!email) {
        alert('Введите email');
        return;
    }
    
    var loginForm = document.getElementById('login-form');
    var loading = document.getElementById('loading');
    
    if (loginForm) loginForm.style.display = 'none';
    if (loading) loading.style.display = 'block';
    
    fetch(API_URL + '/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: email})
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.success && data.token) {
            token = data.token;
            user = data.user;
            localStorage.setItem('falt_token', token);
            localStorage.setItem('falt_user', JSON.stringify(user));
            showPage('home-step1');
            loadMachines();
        } else {
            throw new Error(data.message || 'Ошибка входа');
        }
    })
    .catch(function(e) {
        alert('Ошибка: ' + e.message);
        if (loginForm) loginForm.style.display = 'block';
        if (loading) loading.style.display = 'none';
    });
}

function logout() {
    token = null;
    user = null;
    localStorage.removeItem('falt_token');
    localStorage.removeItem('falt_user');
    showPage('login');
}

function apiGet(endpoint) {
    return fetch(API_URL + endpoint, {
        headers: {'Authorization': 'Bearer ' + token}
    }).then(function(res) {
        if (!res.ok) throw new Error('API Error');
        return res.json();
    });
}

function apiPost(endpoint, data) {
    return fetch(API_URL + endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(data)
    }).then(function(res) {
        if (!res.ok) {
            return res.json().then(function(err) {
                throw new Error(err.detail || 'Error');
            });
        }
        return res.json();
    });
}

function updateHeaderBalance() {
    if (!user) return;
    var balance = user.wallet || 0;
    var el1 = document.getElementById('header-balance'); // для home-step1
    var el2 = document.getElementById('balance');        // возможно другое ID
    var el3 = document.getElementById('balance2');       // для home-step2
    var el4 = document.getElementById('balance3');       // для home-step3
    
    if (el1) el1.textContent = balance;
    if (el2) el2.textContent = balance;
    if (el3) el3.textContent = balance;
    if (el4) el4.textContent = balance;
}

function renderDays() {
    var container = document.getElementById('days-container');
    if (!container) return;
    
    var days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    var months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    var today = new Date();
    
    var html = '';
    for (var i = 0; i < 7; i++) {
        var date = new Date(today);
        date.setDate(today.getDate() + i);
        var dayName = days[date.getDay()];
        var dayNum = date.getDate();
        var month = months[date.getMonth()];
        var dateStr = ('0' + dayNum).slice(-2) + '.' + ('0' + (date.getMonth() + 1)).slice(-2) + '.' + date.getFullYear();
        
        html += '<div class="day-card ' + (i === 0 ? 'active' : '') + '" data-date="' + dateStr + '" onclick="selectDate(\'' + dateStr + '\', this)">';
        html += '<div class="day-name">' + (i === 0 ? 'Сегодня' : dayName) + '</div>';
        html += '<div class="day-number">' + dayNum + '</div>';
        html += '<div class="day-month">' + month + '</div>';
        html += '</div>';
    }
    container.innerHTML = html;
    
    var firstDate = container.querySelector('.day-card');
    if (firstDate && firstDate.dataset.date) {
        selectedDate = firstDate.dataset.date;
    } else {
        // Fallback если что-то пошло не так
        selectedDate = ('0' + today.getDate()).slice(-2) + '.' + 
                       ('0' + (today.getMonth() + 1)).slice(-2) + '.' + 
                       today.getFullYear();
    }
}

function selectDate(date, element) {
    selectedDate = date;
    document.querySelectorAll('.day-card').forEach(function(el) {
        el.classList.remove('active');
    });
    element.classList.add('active');
}

function loadMachines() {

    if (!selectedDate) {
        var today = new Date();
        selectedDate = ('0' + today.getDate()).slice(-2) + '.' + 
                       ('0' + (today.getMonth() + 1)).slice(-2) + '.' + 
                       today.getFullYear();
    }

    apiGet('/machines').then(function(machines) {
        var container = document.getElementById('machines-list');
        if (!container) return;
        
        var html = '';
        for (var i = 0; i < machines.length; i++) {
            var m = machines[i];
            var icon = m.id === '6' ? '🔥' : '🌀';
            html += '<div class="machine-card" onclick="selectMachine(\'' + m.id + '\', \'' + m.name + '\', ' + m.is_working + ')">';
            html += '<div class="machine-icon">' + icon + '</div>';
            html += '<div class="machine-name">' + m.name + '</div>';
            html += '<div class="machine-price">50 ₽/час</div>';
            html += '</div>';
        }
        container.innerHTML = html;
        updateHeaderBalance();
        renderDays();
    }).catch(function(e) {
        console.error('Ошибка загрузки машин:', e);
    });
}

function selectMachine(id, name, isWorking) {
    if (!isWorking) {
        alert('Машинка на техобслуживании');
        return;
    }
    selectedMachine = {id: id, name: name};
    var title = document.getElementById('selected-machine-name');
    if (title) title.textContent = name;
    loadTimeSlots();
    showPage('home-step2');
}

function backToMachines() {
    showPage('home-step1');
}

function loadTimeSlots() {
    
    if (!selectedDate) {
        var today = new Date();
        selectedDate = ('0' + today.getDate()).slice(-2) + '.' + 
                       ('0' + (today.getMonth() + 1)).slice(-2) + '.' + 
                       today.getFullYear();
    }

    apiGet('/slots/' + selectedDate).then(function(data) {
        var machineData = data.machines[selectedMachine.id];
        var container = document.getElementById('time-slots');
        if (!container) return;
        
        var html = '';
        for (var i = 0; i < machineData.slots.length; i++) {
            var slot = machineData.slots[i];
            var className = slot.available ? 'available' : 'booked';
            var onclick = slot.available ? ' onclick="selectTime(\'' + slot.start + '\', \'' + slot.end + '\')"' : '';
            html += '<div class="time-slot ' + className + '"' + onclick + '>' + slot.start + '</div>';
        }
        container.innerHTML = html;
    }).catch(function(e) {
        console.error('Ошибка загрузки времени:', e);
    });
}

function selectTime(start, end) {
    selectedTime = {start: start, end: end};
    var el1 = document.getElementById('confirm-machine');
    var el2 = document.getElementById('confirm-date');
    var el3 = document.getElementById('confirm-time');
    if (el1) el1.textContent = selectedMachine.name;
    if (el2) el2.textContent = selectedDate;
    if (el3) el3.textContent = start + ' - ' + end;
    showPage('home-step3');
}

function backToTime() {
    showPage('home-step2');
}

function confirmBooking() {
    apiPost('/bookings/create', {
        bookings: [{
            date: selectedDate,
            machine_id: selectedMachine.id,
            start_time: selectedTime.start,
            end_time: selectedTime.end
        }]
    }).then(function(result) {
        user.wallet = result.new_balance;
        localStorage.setItem('falt_user', JSON.stringify(user));
        alert('✅ Забронировано!');
        showPage('bookings');
        loadBookings();
    }).catch(function(e) {
        alert('Ошибка: ' + e.message);
    });
}

function loadBookings() {
    apiGet('/bookings/my').then(function(data) {
        var container = document.getElementById('bookings-list');
        var noBookings = document.getElementById('no-bookings');
        
        if (data.bookings.length === 0) {
            if (container) container.innerHTML = '';
            if (noBookings) noBookings.style.display = 'block';
            return;
        }
        
        if (noBookings) noBookings.style.display = 'none';
        
        var html = '';
        for (var i = 0; i < data.bookings.length; i++) {
            var b = data.bookings[i];
            html += '<div class="booking-card">';
            html += '<div class="booking-header">';
            html += '<span class="booking-date">' + b.date + '</span>';
            html += '<span class="booking-status">Активно</span>';
            html += '</div>';
            html += '<div class="booking-info">🧺 Машинка ' + b.machine_id + ' | 🕐 ' + b.start_time + '-' + b.end_time + '</div>';
            html += '<button class="btn-cancel" onclick="cancelBooking(\'' + b.date + '\', \'' + b.machine_id + '\', \'' + b.start_time + '\', \'' + b.end_time + '\')">Отменить (возврат 50₽)</button>';
            html += '</div>';
        }
        if (container) container.innerHTML = html;
    }).catch(function(e) {
        console.error('Ошибка загрузки записей:', e);
    });
}

function cancelBooking(date, machineId, start, end) {
    if (!confirm('Отменить бронирование?')) return;
    
    apiPost('/bookings/cancel', {
        date: date,
        machine_id: machineId,
        start_time: start,
        end_time: end
    }).then(function(result) {
        user.wallet = result.new_balance;
        localStorage.setItem('falt_user', JSON.stringify(user));
        alert('✅ Отменено, 50₽ возвращено');
        loadBookings();
    }).catch(function(e) {
        alert('Ошибка отмены');
    });
}

function updateProfile() {
    if (!user) return;
    var el1 = document.getElementById('profile-name');
    var el2 = document.getElementById('profile-email');
    var el3 = document.getElementById('profile-balance');
    
    if (el1) el1.textContent = (user.name || '') + ' ' + (user.surname || '');
    if (el2) el2.textContent = user.email || '-';
    if (el3) el3.textContent = (user.wallet || 0) + ' ₽';
}


function showTopupPlaceholder() {
    showPage('topup-placeholder');
}

function showToast(message, type) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'toast ' + (type || 'info') + ' show';
    setTimeout(function() {
        toast.classList.remove('show');
    }, 3000);
}