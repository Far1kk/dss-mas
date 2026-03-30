'use strict';

// ---------------------------------------------------------------------------
// Константы
// ---------------------------------------------------------------------------
const HINTS = {
  'спрогнозировать':    'Спрогнозируй фактический доход по проектам на основе прогнозных данных',
  'классифицировать':   'Классифицируй проекты по уровню риска на основе выработки',
  'найти в БД':         'Найди все активные проекты с просроченной датой оплаты',
  'кластеризовать':     'Кластеризуй контрагентов по объёму выручки',
  'временной ряд':      'Проанализируй динамику выработки по кварталам 2024 года',
};

const DISLIKE_COMMENTS = [
  'Информация некорректна',
  'Не соответствует запросу',
  'SQL-запрос содержит ошибку',
  'Результаты неполные',
  'Объяснение непонятно',
];

const LIKE_COMMENTS = [
  'Точный и полезный ответ',
  'Хорошее объяснение',
  'Результаты соответствуют запросу',
];

// ---------------------------------------------------------------------------
// Состояние
// ---------------------------------------------------------------------------
let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
let currentEventSource = null;
let selectedRating = null;
let selectedComment = null;

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const queryInput   = document.getElementById('query-input');
const sendBtn      = document.getElementById('send-btn');
const providerSel  = document.getElementById('provider-select');
const hintsEl      = document.getElementById('hints');
const resultCard   = document.getElementById('result-card');
const spinnerEl    = document.getElementById('spinner');
const statusText   = document.getElementById('status-text');
const resultBody   = document.getElementById('result-body');
const feedbackRow  = document.getElementById('feedback-row');
const likeBtnEl    = document.getElementById('btn-like');
const dislikeBtnEl = document.getElementById('btn-dislike');
const commentsEl   = document.getElementById('feedback-comments');
const feedbackSent = document.getElementById('feedback-sent');
const errorLine    = document.getElementById('error-line');

// ---------------------------------------------------------------------------
// Инициализация подсказок
// ---------------------------------------------------------------------------
function initHints() {
  Object.entries(HINTS).forEach(([label, example]) => {
    const btn = document.createElement('button');
    btn.className = 'hint-tag';
    btn.textContent = label;
    btn.addEventListener('click', () => {
      queryInput.value = example;
      queryInput.focus();
      autoResize();
    });
    hintsEl.appendChild(btn);
  });
}

// ---------------------------------------------------------------------------
// Авторесайз textarea
// ---------------------------------------------------------------------------
function autoResize() {
  queryInput.style.height = 'auto';
  queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + 'px';
}

queryInput.addEventListener('input', autoResize);
queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitQuery();
  }
});

// ---------------------------------------------------------------------------
// Сброс UI результата
// ---------------------------------------------------------------------------
function resetResult() {
  resultCard.classList.remove('visible');
  resultBody.classList.remove('visible');
  feedbackRow.classList.remove('visible');
  feedbackSent.classList.remove('visible');
  errorLine.classList.remove('visible');
  commentsEl.classList.remove('visible');
  commentsEl.innerHTML = '';
  resultBody.textContent = '';
  errorLine.textContent = '';
  statusText.textContent = 'Обрабатываю запрос...';
  spinnerEl.classList.remove('active');
  selectedRating = null;
  selectedComment = null;
  likeBtnEl.classList.remove('active');
  dislikeBtnEl.classList.remove('active');
}

// ---------------------------------------------------------------------------
// Отправка запроса
// ---------------------------------------------------------------------------
function submitQuery() {
  const query = queryInput.value.trim();
  if (!query) return;

  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }

  resetResult();
  resultCard.classList.add('visible');
  spinnerEl.classList.add('active');
  sendBtn.disabled = true;

  const provider = providerSel.value;
  const url = `/api/chat?query=${encodeURIComponent(query)}&session_id=${encodeURIComponent(sessionId)}&llm_provider=${encodeURIComponent(provider)}`;

  const es = new EventSource(url);
  currentEventSource = es;

  es.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }

    if (data.type === 'status') {
      statusText.textContent = data.content;
    } else if (data.type === 'result') {
      spinnerEl.classList.remove('active');
      statusText.textContent = 'Готово';
      resultBody.textContent = data.content;
      resultBody.classList.add('visible');
      feedbackRow.classList.add('visible');
    } else if (data.type === 'error') {
      spinnerEl.classList.remove('active');
      statusText.textContent = 'Ошибка';
      errorLine.textContent = data.content;
      errorLine.classList.add('visible');
    } else if (data.type === 'done') {
      es.close();
      currentEventSource = null;
      sendBtn.disabled = false;
    }
  };

  es.onerror = () => {
    spinnerEl.classList.remove('active');
    statusText.textContent = 'Ошибка подключения';
    errorLine.textContent = 'Не удалось подключиться к серверу';
    errorLine.classList.add('visible');
    sendBtn.disabled = false;
    es.close();
    currentEventSource = null;
  };
}

sendBtn.addEventListener('click', submitQuery);

// ---------------------------------------------------------------------------
// Обратная связь
// ---------------------------------------------------------------------------
function showComments(rating) {
  commentsEl.innerHTML = '';
  commentsEl.classList.add('visible');
  feedbackSent.classList.remove('visible');

  const comments = rating === 'like' ? LIKE_COMMENTS : DISLIKE_COMMENTS;
  comments.forEach((text) => {
    const tag = document.createElement('button');
    tag.className = 'comment-tag';
    tag.textContent = text;
    tag.addEventListener('click', () => {
      document.querySelectorAll('.comment-tag').forEach(t => t.classList.remove('selected'));
      tag.classList.add('selected');
      selectedComment = text;
      sendFeedback(rating, text);
    });
    commentsEl.appendChild(tag);
  });
}

function sendFeedback(rating, comment) {
  fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, rating, comment }),
  }).then(() => {
    feedbackSent.classList.add('visible');
  }).catch(() => {});
}

likeBtnEl.addEventListener('click', () => {
  selectedRating = 'like';
  likeBtnEl.classList.add('active');
  dislikeBtnEl.classList.remove('active');
  showComments('like');
});

dislikeBtnEl.addEventListener('click', () => {
  selectedRating = 'dislike';
  dislikeBtnEl.classList.add('active');
  likeBtnEl.classList.remove('active');
  showComments('dislike');
});

// ---------------------------------------------------------------------------
// Старт
// ---------------------------------------------------------------------------
initHints();
