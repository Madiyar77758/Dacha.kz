// Dacha.kz — клиентские скрипты

// CSRF-токен из cookie (Django)
function getCookie(name) {
  const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return m ? m.pop() : '';
}

// Переключение избранного без перезагрузки страницы
async function toggleFavorite(btn, propertyId) {
  try {
    const res = await fetch(`/favorites/toggle/${propertyId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    if (res.status === 401) { window.location.href = '/accounts/login/'; return; }
    const data = await res.json();
    btn.classList.toggle('active', data.favorited);
    btn.setAttribute('aria-pressed', data.favorited);
    const icon = data.favorited ? '❤️' : '🤍';
    const ico = btn.querySelector('.fav-ico');
    if (ico) {
      ico.textContent = icon;                      // текстовая кнопка (детали)
      const label = btn.querySelector('.fav-label');
      if (label) label.textContent = data.favorited ? 'В избранном' : 'В избранное';
    } else {
      btn.textContent = icon;                      // круглая кнопка-сердечко (карточки)
    }
  } catch (e) { /* тихо игнорируем сетевые сбои */ }
}

// Делегирование: клик по любому .fav-btn
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.fav-btn');
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  toggleFavorite(btn, btn.dataset.id);
});
