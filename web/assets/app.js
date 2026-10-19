/* ==========================================================================
   TTPU Timetable — клиентская логика.
   Без сборки и зависимостей: чистый JS, офлайн-кэш в localStorage,
   живое обновление «сейчас идёт» без перерисовки.
   ========================================================================== */
(() => {
  'use strict';

  /* ── Словари ─────────────────────────────────────────────────────────── */
  const I18N = {
    ru: {
      'brand.sub': 'Расписание',
      'nav.overview': 'Обзор',
      'nav.groups': 'Группы',
      'nav.teachers': 'Преподаватели',
      'nav.rooms': 'Аудитории',
      'nav.search': 'Поиск',
      'nav.back': 'Назад',
      'a11y.skip': 'Перейти к содержанию',
      'home.eyebrow': 'Турниский политехнический университет',
      'home.title.a': 'Расписание,',
      'home.title.b': 'которое дышит',
      'home.lede': 'Пары, преподаватели и аудитории — в одном месте. Открывается мгновенно и продолжает работать без интернета.',
      'home.search': 'Группа, преподаватель или аудитория',
      'home.search.btn': 'Найти',
      'home.now': 'Сейчас',
      'home.your.group': 'Ваша группа',
      'home.change': 'сменить',
      'home.recent': 'Недавние',
      'home.clear': 'очистить',
      'home.choose': 'Выбрать группу',
      'home.next': 'Далее',
      'home.none': 'Пар впереди нет',
      'home.today': 'Сегодня',
      'home.tomorrow': 'Завтра',
      'home.week': 'Неделя',
      'home.teacher': 'Преподаватель',
      'home.room': 'Аудитория',
      'home.bot': 'Бот в Telegram',
      'browse.search': 'Начните вводить название',
      'browse.class': 'Группы',
      'browse.teacher': 'Преподаватели',
      'browse.room': 'Аудитории',
      'browse.class.text': 'Выберите группу, чтобы увидеть её расписание на неделю.',
      'browse.teacher.text': 'Расписание занятий преподавателя по дням недели.',
      'browse.room.text': 'Какие пары проходят в аудитории — по дням недели.',
      'browse.all': 'Все',
      'browse.empty': 'Ничего не найдено',
      'browse.empty.text': 'Попробуйте другое написание или латиницу.',
      'sched.week': 'Неделя',
      'sched.day': 'День',
      'sched.offline': 'Сохранить офлайн',
      'sched.saved': 'Сохранено офлайн',
      'sched.empty.week': 'На этой неделе пар нет',
      'sched.empty.day': 'В этот день пар нет',
      'sched.lessons': 'пар',
      'sched.no-lessons': 'Свободно',
      'sched.back': 'Назад',
      'sched.group': 'Группа',
      'sched.teacher': 'Преподаватель',
      'sched.room': 'Аудитория',
      'sched.week.of': 'Неделя',
      'sched.updated': 'Обновлено',
      'sched.offline.tag': 'офлайн-копия',
      'sched.lessons.week': 'пар на неделе',
      'chip.group': 'подгруппа',
      'search.ph': 'Поиск по группам, преподавателям, аудиториям',
      'search.hint': 'Введите минимум два символа',
      'search.recent': 'Недавние',
      'menu.title': 'Меню',
      'menu.lang': 'Язык',
      'menu.theme': 'Оформление',
      'menu.theme.auto': 'Авто',
      'menu.theme.light': 'Светлое',
      'menu.theme.dark': 'Тёмное',
      'menu.offline': 'Офлайн-копия',
      'menu.bot': 'Открыть бота',
      'foot.brand': 'Расписание',
      'foot.note': 'Данные загружаются из открытого расписания EduPage. Приложение сохраняет расписание на устройстве, поэтому работает офлайн.',
      'foot.bot': 'Телеграм-бот',
      'foot.install': 'Установить',
      'status.offline': 'Офлайн · данные от {time}',
      'status.online': 'Снова онлайн · обновлено {time}',
      'status.nocache': 'Нет сети и нет сохранённых данных',
      'toast.copied': 'Ссылка скопирована',
      'toast.saved': 'Расписание сохранено на устройство',
      'toast.notify': 'Добавить напоминания можно в Telegram-боте',
      'facts.groups': 'групп',
      'facts.groups.sub': 'по всем курсам',
      'facts.teachers': 'преподавателей',
      'facts.teachers.sub': 'ведут занятия',
      'facts.rooms': 'аудиторий',
      'facts.rooms.sub': 'учебные аудитории',
      'facts.lessons': 'занятий',
      'facts.lessons.sub': 'в базе за {n}',
      'unit.week.1': 'неделю',
      'unit.week.2': 'недели',
      'unit.week.5': 'недель',
      'home.pick.eyebrow': 'Начните здесь',
      'home.pick.title': 'Выберите свою группу',
      'home.pick.text': 'Расписание закрепится на главном экране и сохранится на устройстве — дальше оно открывается даже без интернета.',
      'home.pick.popular': 'Популярные группы',
      'home.pick.btn': 'Все группы',
      'live.now': 'идёт сейчас',
      'live.next': 'далее',
      'live.left': 'осталось {n} мин',
      'live.in': 'через {n} мин',
      'live.tomorrow': 'завтра',
      'unit.min': 'мин',
    },
    en: {
      'brand.sub': 'Timetable',
      'nav.overview': 'Overview',
      'nav.groups': 'Classes',
      'nav.teachers': 'Teachers',
      'nav.rooms': 'Rooms',
      'nav.search': 'Search',
      'nav.back': 'Back',
      'a11y.skip': 'Skip to content',
      'home.eyebrow': 'Turin Polytechnic University in Tashkent',
      'home.title.a': 'A timetable',
      'home.title.b': 'that breathes',
      'home.lede': 'Classes, teachers and rooms in one place. Opens instantly and keeps working offline.',
      'home.search': 'Class, teacher or room',
      'home.search.btn': 'Find',
      'home.now': 'Now',
      'home.your.group': 'Your class',
      'home.change': 'change',
      'home.recent': 'Recent',
      'home.clear': 'clear',
      'home.choose': 'Choose a class',
      'home.next': 'Up next',
      'home.none': 'Nothing ahead',
      'home.today': 'Today',
      'home.tomorrow': 'Tomorrow',
      'home.week': 'Week',
      'home.teacher': 'Teacher',
      'home.room': 'Room',
      'home.bot': 'Telegram bot',
      'browse.search': 'Start typing a name',
      'browse.class': 'Classes',
      'browse.teacher': 'Teachers',
      'browse.room': 'Rooms',
      'browse.class.text': 'Pick a class to see its weekly schedule.',
      'browse.teacher.text': "A teacher's classes by weekday.",
      'browse.room.text': 'What is happening in a room, day by day.',
      'browse.all': 'All',
      'browse.empty': 'Nothing found',
      'browse.empty.text': 'Try another spelling or the Latin alphabet.',
      'sched.week': 'Week',
      'sched.day': 'Day',
      'sched.offline': 'Save offline',
      'sched.saved': 'Saved offline',
      'sched.empty.week': 'No classes this week',
      'sched.empty.day': 'No classes on this day',
      'sched.lessons': 'classes',
      'sched.no-lessons': 'Free',
      'sched.back': 'Back',
      'sched.group': 'Class',
      'sched.teacher': 'Teacher',
      'sched.room': 'Room',
      'sched.week.of': 'Week',
      'sched.updated': 'Updated',
      'sched.offline.tag': 'offline copy',
      'sched.lessons.week': 'classes this week',
      'chip.group': 'subgroup',
      'search.ph': 'Search classes, teachers, rooms',
      'search.hint': 'Type at least two characters',
      'search.recent': 'Recent',
      'menu.title': 'Menu',
      'menu.lang': 'Language',
      'menu.theme': 'Appearance',
      'menu.theme.auto': 'Auto',
      'menu.theme.light': 'Light',
      'menu.theme.dark': 'Dark',
      'menu.offline': 'Offline copy',
      'menu.bot': 'Open bot',
      'foot.brand': 'Timetable',
      'foot.note': 'Data comes from the public EduPage timetable. The app stores it on your device, so it works offline.',
      'foot.bot': 'Telegram bot',
      'foot.install': 'Install',
      'status.offline': 'Offline · data from {time}',
      'status.online': 'Back online · updated {time}',
      'status.nocache': 'No network and no saved data',
      'toast.copied': 'Link copied',
      'toast.saved': 'Saved to this device',
      'toast.notify': 'Enable reminders in the Telegram bot',
      'facts.groups': 'classes',
      'facts.groups.sub': 'across all years',
      'facts.teachers': 'teachers',
      'facts.teachers.sub': 'on the staff',
      'facts.rooms': 'rooms',
      'facts.rooms.sub': 'teaching rooms',
      'facts.lessons': 'classes',
      'facts.lessons.sub': 'over {n}',
      'unit.week.1': 'week',
      'unit.week.2': 'weeks',
      'unit.week.5': 'weeks',
      'home.pick.eyebrow': 'Start here',
      'home.pick.title': 'Pick your class',
      'home.pick.text': 'Your timetable will stay on the home screen and be saved on this device, so it opens even without a connection.',
      'home.pick.popular': 'Popular classes',
      'home.pick.btn': 'All classes',
      'live.now': 'in progress',
      'live.next': 'next',
      'live.left': '{n} min left',
      'live.in': 'in {n} min',
      'live.tomorrow': 'tomorrow',
      'unit.min': 'min',
    },
  };

  const MONTHS = {
    ru: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],
    en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
  };
  const WEEKDAYS = {
    ru: ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
    en: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  };
  const WEEKDAYS_SHORT = {
    ru: ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'],
    en: ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'],
  };
  const KIND_LABEL = { class: 'sched.group', teacher: 'sched.teacher', room: 'sched.room' };
  const KINDS = ['class', 'teacher', 'room'];

  /* ── Состояние ───────────────────────────────────────────────────────── */
  const KEY = {
    meta: 'ttpu.meta.v1',
    dir: 'ttpu.dir.v1',
    prefs: 'ttpu.prefs.v1',
    recent: 'ttpu.recent.v1',
    bundle: (kind, id) => `ttpu.bundle.v1.${kind}.${id}`,
  };

  const state = {
    prefs: { lang: 'ru', theme: 'auto' },
    meta: null,
    directory: null,
    bundle: null,
    route: { name: 'home' },
    drift: 0,
    online: navigator.onLine,
    liveTimer: null,
    installEvent: null,
  };

  /* ── Хранилище ───────────────────────────────────────────────────────── */
  const store = {
    get(key, fallback = null) {
      try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
      } catch (error) {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        return false;
      }
    },
    remove(key) {
      try { localStorage.removeItem(key); } catch (error) { /* пусто */ }
    },
  };

  /* ── Утилиты ─────────────────────────────────────────────────────────── */
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

  function t(key, vars) {
    const dict = I18N[state.prefs.lang] || I18N.ru;
    let value = dict[key] || I18N.ru[key] || key;
    if (vars) {
      for (const [name, replacement] of Object.entries(vars)) {
        value = value.replace(new RegExp(`\\{${name}\\}`, 'g'), replacement);
      }
    }
    return value;
  }

  const lang = () => state.prefs.lang;

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function icon(name, className = 'icon') {
    return `<svg class="${className}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
  }

  function naturalCompare(a, b) {
    return String(a).localeCompare(String(b), 'ru', { numeric: true, sensitivity: 'base' });
  }

  function now() {
    return new Date(Date.now() + state.drift);
  }

  function isoDate(date) {
    const pad = (value) => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function minutesOf(hhmm) {
    if (!hhmm || !hhmm.includes(':')) return null;
    const [hours, minutes] = hhmm.split(':').map(Number);
    return Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : null;
  }

  function dateLabel(iso) {
    if (!iso) return '';
    const [year, month, day] = iso.split('-').map(Number);
    if (!year || !month || !day) return '';
    return `${day} ${MONTHS[lang()][month - 1]}`;
  }

  function weekdayShort(index) {
    return (WEEKDAYS_SHORT[lang()] || WEEKDAYS_SHORT.ru)[index] || '';
  }

  /** «19 октября, 11:32» — время сервера как есть, без пересчёта часовых поясов. */
  function stampLabel(value) {
    const text = String(value || '');
    if (text.length < 16) return text;
    return `${dateLabel(text.slice(0, 10))}, ${text.slice(11, 16)}`;
  }

  function weekdayLong(index) {
    return (WEEKDAYS[lang()] || WEEKDAYS.ru)[index] || '';
  }

  function pluralLessons(count) {
    if (lang() === 'en') return count === 1 ? 'class' : 'classes';
    const rest = count % 100;
    if (rest >= 11 && rest <= 14) return 'пар';
    const tail = rest % 10;
    if (tail === 1) return 'пара';
    if (tail >= 2 && tail <= 4) return 'пары';
    return 'пар';
  }

  function groupKey(kind, id) {
    return `${kind}:${id}`;
  }

  function pluralWeeks(count) {
    const rest = Math.abs(count) % 100;
    const tail = rest % 10;
    if (rest >= 11 && rest <= 14) return t('unit.week.5');
    if (tail === 1) return t('unit.week.1');
    if (tail >= 2 && tail <= 4) return t('unit.week.2');
    return t('unit.week.5');
  }

  /** «Неделя 10» — из номера EduPage, иначе порядковая позиция в наборе. */
  function weekLabel(week, fallbackPosition) {
    const number = week && week.number;
    return `${t('sched.week.of')} ${number || fallbackPosition || ''}`.trim();
  }

  function parseRoute() {
    const path = decodeURIComponent(location.pathname);
    const params = new URLSearchParams(location.search);
    const parts = path.split('/').filter(Boolean);
    if (parts.length === 0) return { name: 'home' };
    if (parts[0] === 'browse') {
      const kind = KINDS.includes(parts[1]) ? parts[1] : 'class';
      return { name: 'browse', kind, q: params.get('q') || '' };
    }
    if (KINDS.includes(parts[0]) && parts[1]) {
      return {
        name: 'schedule',
        kind: parts[0],
        id: parts.slice(1).join('/'),
        week: params.get('week') || '',
        view: params.get('view') === 'day' ? 'day' : 'week',
        day: params.get('d') != null ? Number(params.get('d')) : null,
      };
    }
    return { name: 'home' };
  }

  function go(url, replace = false) {
    if (replace) history.replaceState({}, '', url);
    else history.pushState({}, '', url);
    render();
  }

  /* ── API ─────────────────────────────────────────────────────────────── */
  async function api(path, { timeout = 9000 } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(path, { signal: controller.signal, headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  }

  /* ── Работа с расписанием ────────────────────────────────────────────── */
  function weekFor(bundle, isoDay) {
    if (!bundle || !bundle.weeks) return null;
    const numbers = Object.keys(bundle.weeks);
    if (!numbers.length) return null;
    if (isoDay) {
      for (const number of numbers) {
        const week = bundle.weeks[number];
        const end = week.dateto || week.datefrom;
        if (week.datefrom && week.datefrom <= isoDay && isoDay <= end) return week;
      }
    }
    return null;
  }

  function pickWeek(bundle, preferred, isoDay) {
    if (!bundle || !bundle.weeks) return null;
    if (preferred && bundle.weeks[preferred]) return bundle.weeks[preferred];
    return weekFor(bundle, isoDay) || bundle.weeks[Object.keys(bundle.weeks).slice(-1)[0]];
  }

  /** Текущая и ближайшая пара — считается на клиенте по сохранённым данным. */
  function computeUpNext(bundle, moment = now()) {
    const todayIso = isoDate(moment);
    const todayIndex = (moment.getDay() + 6) % 7;
    const nowMinutes = moment.getHours() * 60 + moment.getMinutes();
    let current = null, currentLeft = null, progress = 0, next = null, nextDay = null, nextIn = null;

    const weeks = bundle && bundle.weeks ? Object.values(bundle.weeks) : [];
    const days = [];
    for (const week of weeks) for (const day of week.days || []) days.push(day);
    days.sort((a, b) => String(a.date).localeCompare(String(b.date)));

    const today = days.find((day) => day.date === todayIso) || null;
    const todays = today ? today.lessons : [];

    for (const lesson of todays) {
      const start = minutesOf(lesson.start), end = minutesOf(lesson.end);
      if (start == null || end == null) continue;
      if (start <= nowMinutes && nowMinutes < end) {
        current = lesson; currentLeft = end - nowMinutes;
        progress = (nowMinutes - start) / Math.max(1, end - start);
        break;
      }
    }

    const upcoming = [];
    for (const day of days) {
      for (const lesson of day.lessons || []) {
        const start = minutesOf(lesson.start);
        if (start == null) continue;
        if (day.date === todayIso && start <= nowMinutes) continue;
        if (day.date < todayIso) continue;
        upcoming.push({ date: day.date, day, start, lesson });
      }
    }
    upcoming.sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start));
    if (upcoming.length) {
      const item = upcoming[0];
      next = item.lesson; nextDay = item.day;
      nextIn = item.date === todayIso ? Math.max(1, item.start - nowMinutes) : null;
    }
    const todayMeta = today
      ? { ...today, lessons: undefined }
      : { idx: todayIndex, date: todayIso, ru: weekdayLong(todayIndex), en: weekdayLong(todayIndex), day: moment.getDate(), month: moment.getMonth() + 1 };

    return { current, currentLeft, progress, next, nextDay, nextIn, today: todayMeta };
  }

  function lessonCard(lesson, options = {}) {
    const { kind, day, nowInfo, compact } = options;
    const color = /^#[0-9a-f]{3,8}$/i.test(lesson.color || '') ? lesson.color : 'var(--accent)';
    const subject = lesson.short || lesson.subject || '—';
    const full = lesson.subject && lesson.subject !== subject ? lesson.subject : '';
    const rows = [];
    const chips = [];

    if (kind === 'class') {
      for (const teacher of lesson.teachers || []) rows.push(['user', teacher.short || teacher.name]);
      for (const room of lesson.rooms || []) rows.push(['pin', room.name]);
    } else if (kind === 'teacher') {
      for (const klass of lesson.classes || []) rows.push(['grid', klass.name]);
      for (const room of lesson.rooms || []) rows.push(['pin', room.name]);
    } else {
      for (const teacher of lesson.teachers || []) rows.push(['user', teacher.short || teacher.name]);
      for (const klass of lesson.classes || []) chips.push(klass.name);
    }
    for (const name of lesson.groups || []) chips.push(name);

    const start = minutesOf(lesson.start);
    const isNow = !!(nowInfo && nowInfo.current && nowInfo.current.key === lesson.key &&
      nowInfo.today && day && nowInfo.today.date === day.date) ||
      !!(nowInfo && nowInfo.currentKey && nowInfo.currentKey === lesson.key);
    const isNext = !!(nowInfo && nowInfo.nextKey && nowInfo.nextKey === lesson.key);
    const isPast = !isNow && start != null && day && day.date &&
      (day.date < nowInfo.todayIso ||
        (day.date === nowInfo.todayIso && start + 0 < nowInfo.nowMinutes - 0 && !isNext &&
          lesson.end && minutesOf(lesson.end) <= nowInfo.nowMinutes));

    const classes = ['lesson'];
    if (isNow) classes.push('is-now');
    else if (isPast) classes.push('is-past');
    if (isNext) classes.push('is-next');

    return `
      <article class="${classes.join(' ')}" style="--c:${esc(color)}"
               data-key="${esc(lesson.key)}" data-start="${esc(lesson.start)}"
               data-end="${esc(lesson.end)}" data-date="${esc(day ? day.date : '')}">
        <div class="lesson__time">
          <span>${esc(lesson.start)}–${esc(lesson.end)}</span>
          <em>${esc(lesson.period)}</em>
        </div>
        <h3 class="lesson__subject">${esc(subject)}</h3>
        ${full ? `<p class="lesson__meta">${esc(full)}</p>` : ''}
        ${rows.length ? `<div class="lesson__rows">${rows.map(([name, text]) =>
          `<span class="lesson__row">${icon(name)}${esc(text)}</span>`).join('')}</div>` : ''}
        ${chips.length ? `<div class="lesson__tags">${chips.map((text) =>
          `<span class="chip">${esc(text)}</span>`).join('')}</div>` : ''}
        ${isNow ? '<div class="lesson__live"><span></span></div>' : ''}
      </article>`;
  }

  function liveContext(bundle, moment = now()) {
    const todayIso = isoDate(moment);
    const memory = state.live || {};
    return {
      todayIso,
      nowMinutes: moment.getHours() * 60 + moment.getMinutes(),
      currentKey: memory.currentKey || null,
      nextKey: memory.nextKey || null,
    };
  }

  /* ── Рендер: обзор ───────────────────────────────────────────────────── */
  function renderHome() {
    const meta = state.meta || {};

    $('#foot-updated').textContent = meta.updated_at
      ? `${t('sched.updated')}: ${stampLabel(meta.updated_at)}`
      : '';
    const facts = $('#facts');
    const weeks = meta.weeks || Object.keys((state.directory || {}).week || {}).length || 0;
    facts.innerHTML = [
      ['facts.groups', meta.classes, t('facts.groups.sub')],
      ['facts.teachers', meta.teachers, t('facts.teachers.sub')],
      ['facts.rooms', meta.classrooms, t('facts.rooms.sub')],
      ['facts.lessons', meta.lessons, t('facts.lessons.sub', { n: `${weeks} ${pluralWeeks(weeks)}` })],
    ].filter(([, value]) => value).map(([label, value, sub]) => `
      <div><dt>${esc(t(label))}</dt><dd>${esc(value)}${sub ? `<small>${esc(sub)}</small>` : ''}</dd></div>
    `).join('');

    const quick = [
      ['calendar', t('home.today'), () => openMyDay(0)],
      ['clock', t('home.tomorrow'), () => openMyDay(1)],
      ['grid', t('home.week'), () => openMyWeek()],
      ['user', t('home.teacher'), () => go('/browse/teacher')],
      ['pin', t('home.room'), () => go('/browse/room')],
    ];
    if (meta.bot_url) quick.push(['telegram', t('home.bot'), () => window.open(meta.bot_url, '_blank')]);
    $('#quick').innerHTML = quick.map(([name, label], index) =>
      `<button type="button" data-quick="${index}">${icon(name)}<span>${esc(label)}</span></button>`).join('');
    $$('#quick button').forEach((button, index) => {
      button.addEventListener('click', quick[index][2]);
    });

    renderRecent();
    renderGroupCard();
    renderNowCard();
    updateBotLinks();
  }

  function renderRecent() {
    const recent = store.get(KEY.recent, []);
    const wrap = $('#recent');
    const shelf = $('#shelf-recent');
    $('#clear-recent').hidden = recent.length === 0;
    shelf.hidden = recent.length === 0;
    if (!recent.length) return;
    wrap.innerHTML = recent.slice(0, 8).map((item) => `
      <a href="/${item.kind}/${encodeURIComponent(item.id)}" data-link>
        <span class="kind">${esc(item.kind === 'class' ? 'гр' : item.kind === 'teacher' ? 'преп' : 'ауд')}</span>
        <span>${esc(item.name)}</span>
      </a>`).join('');
  }

  async function renderGroupCard() {
    const card = $('#group-card');
    const saved = savedGroup();
    document.body.classList.toggle('is-fresh', !saved);
    if (!saved) { card.hidden = true; renderPickCard(); return; }
    $('#pick-card').hidden = true;
    card.hidden = false;
    $('#group-name').textContent = saved.name;

    let bundle = store.get(KEY.bundle('class', saved.id));
    if (!bundle) {
      try {
        bundle = await api(`/api/offline/class/${encodeURIComponent(saved.id)}`);
        store.set(KEY.bundle('class', saved.id), bundle);
      } catch (error) { /* офлайн и нет копии */ }
    }
    const week = pickWeek(bundle, '', isoDate(now()));
    const days = week ? week.days : [];
    const total = days.reduce((sum, day) => sum + day.count, 0);
    const todayIndex = (now().getDay() + 6) % 7;
    $('#group-meta').innerHTML = `${total} ${esc(t('sched.lessons.week'))} · ${esc(week ? week.title : '—')}`;
    $('#group-days').innerHTML = days.map((day) => `
      <span class="${day.count ? '' : 'is-empty'} ${day.idx === todayIndex ? 'is-today' : ''}"
            data-day="${day.idx}" role="button" tabindex="0">${esc(weekdayShort(day.idx))} ${day.count || '·'}</span>`).join('');
    $$('#group-days span').forEach((node) => {
      node.addEventListener('click', () => {
        go(`/class/${encodeURIComponent(saved.id)}?view=day&d=${node.dataset.day}`);
      });
    });
  }

  function renderPickCard() {
    const card = $('#pick-card');
    card.hidden = false;
    const popular = ((state.directory || {}).popular || []).slice(0, 6);
    const box = $('#pick-chips');
    if (!popular.length) { box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = popular.map((item) => `
      <a href="/class/${encodeURIComponent(item.id)}" data-link
         data-kind="class" data-id="${esc(item.id)}" data-name="${esc(item.name)}"
         style="--dot:${/^#/.test(item.color || '') ? esc(item.color) : 'var(--hairline)'}">
        <span class="row__dot"></span>${esc(item.name)}
      </a>`).join('');
  }

  async function renderNowCard() {
    const card = $('#now-card');
    const saved = savedGroup();
    if (!saved) { card.hidden = true; return; }
    card.hidden = false;

    let bundle = store.get(KEY.bundle('class', saved.id));
    if (!bundle) {
      try {
        bundle = await api(`/api/offline/class/${encodeURIComponent(saved.id)}`);
        store.set(KEY.bundle('class', saved.id), bundle);
      } catch (error) { card.hidden = true; return; }
    }
    paintNowCard(computeUpNext(bundle));
  }

  function paintNowCard(info) {
    if (!info) return;
    state.live = info;
    const moment = now();
    $('#now-clock').textContent = `${String(moment.getHours()).padStart(2, '0')}:${String(moment.getMinutes()).padStart(2, '0')}`;

    const subject = $('#now-subject');
    const metaNode = $('#now-meta');
    const leftNode = $('#now-left');
    const nextNode = $('#now-next');
    const progress = $('#now-progress');
    const eyebrow = $('#now-card .eyebrow');

    if (info.current) {
      const lesson = info.current;
      eyebrow.className = 'eyebrow eyebrow--live';
      eyebrow.textContent = t('home.now');
      subject.textContent = lesson.short || lesson.subject;
      metaNode.innerHTML = `${esc(lesson.start)}–${esc(lesson.end)}` +
        (lesson.rooms || []).map((room) => ` <span class="chip">${esc(room.name)}</span>`).join('') +
        (lesson.teachers || []).map((teacher) => ` <span class="chip">${esc(teacher.short || teacher.name)}</span>`).join('');
      progress.hidden = false;
      progress.querySelector('span').style.width = `${Math.round(info.progress * 100)}%`;
      leftNode.textContent = t('live.left', { n: info.currentLeft });
    } else {
      eyebrow.className = 'eyebrow';
      eyebrow.textContent = t('home.next');
      progress.hidden = true;
      if (info.next) {
        const lesson = info.next;
        subject.textContent = lesson.short || lesson.subject;
        const dayName = info.nextDay
          ? (info.nextDay.date === isoDate(now())
            ? t('home.today')
            : (info.nextIn == null ? `${weekdayShort(info.nextDay.idx)} · ${dateLabel(info.nextDay.date)}` : t('home.today')))
          : '';
        metaNode.innerHTML = [`${esc(lesson.start)}–${esc(lesson.end)}`, esc(dayName),
          ...(lesson.rooms || []).map((room) => `<span class="chip">${esc(room.name)}</span>`)].filter(Boolean).join(' · ');
        leftNode.textContent = info.nextIn != null ? t('live.in', { n: info.nextIn }) : '';
      } else {
        subject.textContent = t('home.none');
        metaNode.textContent = '';
        leftNode.textContent = '';
      }
    }
    nextNode.innerHTML = info.current && info.next
      ? `${icon('bolt')} ${esc(t('home.next'))}: <b>${esc(info.next.short || info.next.subject)}</b> · ${esc(info.next.start)} ${info.nextIn != null ? `(${esc(t('live.in', { n: info.nextIn }))})` : ''}`
      : '';
  }

  /* ── Сохранённая группа ──────────────────────────────────────────────── */
  function savedGroup() {
    const prefs = store.get(KEY.prefs, {});
    return prefs.group ? prefs.group : null;
  }

  function saveGroup(id, name) {
    const prefs = store.get(KEY.prefs, {});
    prefs.group = { id, name };
    store.set(KEY.prefs, prefs);
    remember(kind_safe('class'), id, name);
  }
  const kind_safe = (kind) => kind;

  function remember(kind, id, name) {
    const recent = store.get(KEY.recent, []).filter((item) => !(item.kind === kind && item.id === id));
    recent.unshift({ kind, id, name });
    store.set(KEY.recent, recent.slice(0, 8));
  }

  /* ── Рендер: справочник ──────────────────────────────────────────────── */
  function catalogue(kind) {
    const directory = state.directory;
    if (!directory) return [];
    const items = (directory[kind === 'class' ? 'classes' : kind === 'teacher' ? 'teachers' : 'classrooms'] || [])
      .map((item) => ({ ...item, load: (directory.load || {})[`${kind}:${item.id}`] || 0 }));
    return items.sort((a, b) => naturalCompare(a.name, b.name));
  }

  function classSection(name) {
    const match = /-?(\d{2})$/.exec(name || '');
    if (!match) return { key: 'other', label: lang() === 'ru' ? 'Прочие' : 'Other' };
    const year = match[1];
    const course = { 26: 1, 25: 2, 24: 3, 23: 4, 22: 5 }[year];
    const label = course
      ? (lang() === 'ru' ? `${course} курс` : `Year ${course}`)
      : (lang() === 'ru' ? `Набор 20${year}` : `Cohort 20${year}`);
    return { key: String(100 - Number(year)), label: `${label} · 20${year}` };
  }

  function groupedItems(kind, items) {
    const groups = new Map();
    for (const item of items) {
      let key, label;
      if (kind === 'class') {
        const section = classSection(item.name);
        key = section.key; label = section.label;
      } else if (kind === 'teacher') {
        const letter = (item.short || item.name || '#')[0].toUpperCase();
        key = letter; label = letter;
      } else {
        const first = (item.name || '#')[0];
        const numeric = /\d/.test(first);
        key = numeric ? '0' : '1';
        label = numeric ? (lang() === 'ru' ? 'Нумерованные' : 'Numbered') : (lang() === 'ru' ? 'С залами' : 'Named halls');
      }
      if (!groups.has(key)) groups.set(key, { label, items: [] });
      groups.get(key).items.push(item);
    }
    return Array.from(groups.entries())
      .sort((a, b) => naturalCompare(a[0], b[0]))
      .map(([, value]) => value);
  }

  function renderBrowse() {
    const kind = state.route.kind || 'class';
    $('#browse-title').textContent = t(`browse.${kind}`);
    $('#browse-text').textContent = t(`browse.${kind}.text`);
    $('#browse-back').setAttribute('href', '/');
    const input = $('#browse-input');
    if (document.activeElement !== input) input.value = state.route.q || '';
    $$('#browse-tabs button').forEach((button) => {
      button.classList.toggle('is-on', button.dataset.kind === kind);
    });
    paintBrowseList();
  }

  function paintBrowseList() {
    const kind = state.route.kind || 'class';
    const query = ($('#browse-input').value || '').trim().toLowerCase();
    const all = catalogue(kind);
    const items = query
      ? all.filter((item) => (item.name || '').toLowerCase().includes(query)
        || (item.short || '').toLowerCase().includes(query))
      : all;
    $('#browse-clear').hidden = !query;
    const list = $('#browse-list');

    if (!items.length) {
      list.innerHTML = `<div class="empty"><strong>${esc(t('browse.empty'))}</strong>${esc(t('browse.empty.text'))}</div>`;
      return;
    }
    list.innerHTML = groupedItems(kind, items).map((group) => `
      <section class="catalog__group">
        <p class="catalog__label">${esc(group.label)} <span>${group.items.length}</span></p>
        <div class="catalog__items">
          ${group.items.map((item) => {
            const load = item.load ? `${item.load} ${pluralLessons(item.load)}` : '';
            const sub = [item.short && item.short !== item.name ? item.short : '', load].filter(Boolean).join(' · ');
            return `
              <a class="row" href="/${kind}/${encodeURIComponent(item.id)}" data-link
                 data-kind="${kind}" data-id="${esc(item.id)}" data-name="${esc(item.name)}">
                <span class="row__dot" style="--dot:${/^#/.test(item.color || '') ? esc(item.color) : 'var(--hairline)'}"></span>
                <span class="row__body">
                  <span class="row__name">${esc(item.name)}</span>
                  ${sub ? `<span class="row__sub">${esc(sub)}</span>` : ''}
                </span>
                <span class="row__go">${icon('arrow')}</span>
              </a>`;
          }).join('')}
        </div>
      </section>`).join('');
  }

  /* ── Рендер: расписание ──────────────────────────────────────────────── */
  async function renderSchedule() {
    const { kind, id } = state.route;
    const title = $('#schedule-title');
    const stamp = $('#schedule-stamp');
    $('#schedule-kind').textContent = t(KIND_LABEL[kind] || 'sched.group');
    $('#schedule-back').setAttribute('href', `/browse/${kind}`);

    let bundle = store.get(KEY.bundle(kind, id));
    const cached = !!bundle;
    if (!bundle) {
      $('#week-grid').innerHTML = skeletonGrid();
      $('#week-grid').hidden = false;
      $('#day-view').hidden = true;
      try {
        bundle = await api(`/api/offline/${kind}/${encodeURIComponent(id)}`, { timeout: 12000 });
        store.set(KEY.bundle(kind, id), bundle);
      } catch (error) {
        title.textContent = '—';
        stamp.textContent = t('status.nocache');
        $('#week-grid').innerHTML = `<div class="empty"><strong>${esc(t('browse.empty'))}</strong>${esc(t('status.nocache'))}</div>`;
        return;
      }
    }
    state.bundle = bundle;

    const entity = bundle.entity || { name: id };
    title.textContent = entity.name || id;
    document.title = `${entity.name || id} · TTPU`;
    remember(kind, id, entity.name || id);

    const moment = now();
    const week = pickWeek(bundle, state.route.week, isoDate(moment));
    if (!week) {
      stamp.textContent = '';
      $('#week-grid').innerHTML = `<div class="empty"><strong>${esc(t('sched.empty.week'))}</strong></div>`;
      return;
    }
    state.live = computeUpNext(bundle, moment);

    const numbers = Object.keys(bundle.weeks);
    const position = numbers.indexOf(week.tt_num);
    $('#weeknav').innerHTML = `
      <button class="weeknav__btn" data-week-nav="-1" ${position <= 0 ? 'disabled' : ''} aria-label="Предыдущая неделя">${icon('back')}</button>
      <span class="weeknav__label">${esc(weekLabel(week, position + 1))}<small>${esc(dateLabel(week.monday))} – ${esc(dateLabel(week.dateto))}</small></span>
      <button class="weeknav__btn" data-week-nav="1" ${position >= numbers.length - 1 ? 'disabled' : ''} aria-label="Следующая неделя">${icon('next')}</button>`;

    $('#view-switch').querySelectorAll('button').forEach((button) => {
      button.classList.toggle('is-on', button.dataset.view === state.route.view);
    });

    const todayIndex = (moment.getDay() + 6) % 7;
    const view = state.route.view;
    const activeDay = state.route.day != null && !Number.isNaN(state.route.day)
      ? state.route.day
      : (week.days.some((day) => day.idx === todayIndex && day.count) ? todayIndex : firstDayWithLessons(week.days));

    $('#daytabs').hidden = view !== 'day';
    $('#week-grid').hidden = view !== 'week';
    $('#day-view').hidden = view !== 'day';

    if (view === 'day') renderDayView(week, activeDay, todayIndex, kind);
    else renderWeekView(week, todayIndex, kind);

    const total = week.days.reduce((sum, day) => sum + day.count, 0);
    const updated = stampLabel(bundle.updated_at);
    stamp.innerHTML = `${esc(weekLabel(week, position + 1))} · <b>${total}</b> ${esc(pluralLessons(total))}` +
      (updated ? ` · ${esc(t('sched.updated'))} <span class="mono">${esc(updated)}</span>` : '') +
      (cached && !state.online ? ` · ${esc(t('sched.offline.tag'))}` : '');
    paintLive();
  }

  function firstDayWithLessons(days) {
    const found = days.find((day) => day.count);
    return found ? found.idx : 0;
  }

  function renderWeekView(week, todayIndex, kind) {
    $('#week-grid').innerHTML = week.days.map((day) => `
      <div class="grid__col ${day.idx === todayIndex ? 'is-today' : ''} ${day.count ? '' : 'is-empty'}">
        <div class="grid__head"><b>${esc(weekdayShort(day.idx))}</b><span>${esc(dateLabel(day.date))}</span></div>
        ${day.count
          ? day.lessons.map((lesson) => lessonCard(lesson, { kind, day, nowInfo: liveContext() })).join('')
          : `<div class="grid__empty">${esc(t('sched.no-lessons'))}</div>`}
      </div>`).join('');
  }

  function renderDayView(week, activeDay, todayIndex, kind) {
    $('#daytabs').innerHTML = week.days.map((day) => `
      <button type="button" data-day="${day.idx}"
              class="${day.idx === activeDay ? 'is-on' : ''} ${day.idx === todayIndex ? 'is-today' : ''}">
        <b>${esc(weekdayShort(day.idx))}</b><span>${day.count ? day.count + ' ' + pluralLessons(day.count) : '—'}</span>
      </button>`).join('');

    const day = week.days[activeDay] || week.days[0];
    if (!day || !day.count) {
      $('#day-view').innerHTML = `<div class="empty"><strong>${esc(weekdayLong(day ? day.idx : 0))}</strong>${esc(t('sched.empty.day'))}</div>`;
      return;
    }
    $('#day-view').innerHTML = day.lessons.map((lesson) => `
      <div class="timeline__row">
        <div class="timeline__time">${esc(lesson.start)}<small>${esc(lesson.end)}</small></div>
        <div class="timeline__body">${lessonCard(lesson, { kind, day, nowInfo: liveContext() })}</div>
      </div>`).join('');
  }

  function skeletonGrid() {
    return `<div class="grid">${Array.from({ length: 6 }, () =>
      `<div class="grid__col"><div class="sk-line skeleton" style="width:60%"></div>
       <div class="sk-card skeleton"></div><div class="sk-card skeleton"></div></div>`).join('')}</div>`;
  }

  /* ── Живые маркеры ───────────────────────────────────────────────────── */
  function paintLive() {
    const moment = now();
    const todayIso = isoDate(moment);
    const nowMinutes = moment.getHours() * 60 + moment.getMinutes();
    const info = state.bundle ? computeUpNext(state.bundle, moment) : null;
    state.live = info || {};
    state.live.todayIso = todayIso;
    state.live.nowMinutes = nowMinutes;
    state.live.currentKey = info && info.current ? info.current.key : null;
    state.live.nextKey = info && info.next ? info.next.key : null;

    $$('.lesson').forEach((node) => {
      const date = node.dataset.date;
      const start = minutesOf(node.dataset.start);
      const end = minutesOf(node.dataset.end);
      const isNow = !!(info && info.current && info.current.key === node.dataset.key && date === todayIso);
      const isNext = !!(info && info.next && info.next.key === node.dataset.key && date === todayIso);
      const isPast = !!(date && (date < todayIso || (date === todayIso && end != null && end <= nowMinutes)));
      node.classList.toggle('is-now', isNow);
      node.classList.toggle('is-next', !isNow && isNext);
      node.classList.toggle('is-past', !isNow && !isNext && isPast);

      const live = node.querySelector('.lesson__live');
      if (isNow && start != null && end != null) {
        if (!live) {
          const bar = document.createElement('div');
          bar.className = 'lesson__live';
          bar.innerHTML = '<span></span>';
          node.appendChild(bar);
        }
        const ratio = Math.min(1, Math.max(0, (nowMinutes - start) / Math.max(1, end - start)));
        node.querySelector('.lesson__live span').style.width = `${Math.round(ratio * 100)}%`;
      } else if (live) {
        live.remove();
      }
    });

    if (!$('#screen-home').hidden && savedGroup()) paintNowCard(info);
  }

  function startLiveTimer() {
    clearInterval(state.liveTimer);
    state.liveTimer = setInterval(() => {
      paintLive();
      if (!$('#screen-home').hidden) {
        const moment = now();
        const clock = $('#now-clock');
        if (clock) clock.textContent = `${String(moment.getHours()).padStart(2, '0')}:${String(moment.getMinutes()).padStart(2, '0')}`;
      }
    }, 20000);
  }

  /* ── Поиск ───────────────────────────────────────────────────────────── */
  let searchTimer = null;
  let finderTimer = null;

  function localSearch(query, limit = 12) {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2 || !state.directory) return [];
    const out = [];
    for (const kind of KINDS) {
      for (const item of catalogue(kind)) {
        if ((item.name || '').toLowerCase().includes(needle) || (item.short || '').toLowerCase().includes(needle)) {
          out.push({ kind, ...item });
          if (out.length >= limit) return out;
        }
      }
    }
    return out;
  }

  function resultRow(item, index) {
    const kindLabel = item.kind === 'class' ? t('nav.groups') : item.kind === 'teacher' ? t('nav.teachers') : t('nav.rooms');
    const load = item.load ? `${item.load} ${pluralLessons(item.load)}` : '';
    return `
      <a class="row" href="/${item.kind}/${encodeURIComponent(item.id)}" data-link style="--i:${index}"
         data-kind="${item.kind}" data-id="${esc(item.id)}" data-name="${esc(item.name)}">
        <span class="row__dot" style="--dot:${/^#/.test(item.color || '') ? esc(item.color) : 'var(--hairline)'}"></span>
        <span class="row__body">
          <span class="row__name">${esc(item.name)}</span>
          <span class="row__sub">${esc(kindLabel)}${load ? ' · ' + esc(load) : ''}</span>
        </span>
        <span class="row__go">${icon('arrow')}</span>
      </a>`;
  }

  function renderSearchResults(items, query) {
    const body = $('#search-results');
    if (!query || query.trim().length < 2) {
      const recent = store.get(KEY.recent, []);
      body.innerHTML = `<p class="overlay__label">${esc(t('search.hint'))}</p>`;
      if (recent.length) {
        body.insertAdjacentHTML('beforeend',
          `<p class="overlay__label">${esc(t('search.recent'))}</p>` +
          recent.map((item, index) => resultRow({ ...item, load: 0 }, index)).join(''));
      }
      return;
    }
    if (!items.length) {
      body.innerHTML = `<div class="empty"><strong>${esc(t('browse.empty'))}</strong>${esc(t('browse.empty.text'))}</div>`;
      return;
    }
    body.innerHTML = items.map((item, index) => resultRow(item, index)).join('');
  }

  async function runSearch(query) {
    let items = localSearch(query, 14);
    if (state.online && query.trim().length >= 2) {
      try {
        const remote = await api(`/api/search?q=${encodeURIComponent(query)}`);
        const merged = [];
        const seen = new Set();
        for (const item of [...remote, ...items]) {
          const key = groupKey(item.kind, item.id);
          if (seen.has(key)) continue;
          seen.add(key);
          merged.push(item);
        }
        items = merged.slice(0, 16);
      } catch (error) { /* остаёмся на локальных результатах */ }
    }
    renderSearchResults(items, query);
  }

  function openSearch() {
    $('#search-overlay').hidden = false;
    document.body.classList.add('is-locked');
    const input = $('#search-input');
    input.value = '';
    renderSearchResults([], '');
    setTimeout(() => input.focus(), 60);
  }

  function closeSearch() {
    $('#search-overlay').hidden = true;
    document.body.classList.remove('is-locked');
  }

  /* ── Меню ────────────────────────────────────────────────────────────── */
  function openMenu() {
    $('#menu-overlay').hidden = false;
    document.body.classList.add('is-locked');
    $('#btn-menu').setAttribute('aria-expanded', 'true');
    paintMenu();
  }

  function closeMenu() {
    $('#menu-overlay').hidden = true;
    document.body.classList.remove('is-locked');
    $('#btn-menu').setAttribute('aria-expanded', 'false');
  }

  function paintMenu() {
    $$('#menu-theme button').forEach((button) => {
      button.classList.toggle('is-on', button.dataset.themeOpt === state.prefs.theme);
    });
    const meta = state.meta || {};
    $('#menu-offline-value').textContent = meta.updated_at ? stampLabel(meta.updated_at) : '—';
    const bundles = Object.keys(localStorage).filter((key) => key.startsWith('ttpu.bundle')).length;
    $('#menu-version').textContent = `v2.0 · ${bundles} ${lang() === 'ru' ? 'сохр.' : 'saved'}`;
    $('#menu-bot').href = meta.bot_url || '#';
    $('#menu-bot').hidden = !meta.bot_url;
  }

  function updateBotLinks() {
    const url = (state.meta || {}).bot_url;
    const link = $('#foot-bot');
    link.hidden = !url;
    if (url) link.href = url;
    if ($('#menu-bot')) {
      $('#menu-bot').href = url || '#';
      $('#menu-bot').hidden = !url;
    }
  }

  /* ── Тема и язык ─────────────────────────────────────────────────────── */
  function applyTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const resolved = state.prefs.theme === 'auto' ? (prefersDark ? 'dark' : 'light') : state.prefs.theme;
    document.documentElement.dataset.theme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]:not([media])');
    const color = resolved === 'dark' ? '#0d0c0b' : '#f4f1ea';
    if (meta) meta.setAttribute('content', color);
  }

  function applyLang() {
    document.documentElement.lang = lang();
    document.documentElement.dataset.lang = lang();
    $$('[data-i18n]').forEach((node) => {
      const value = t(node.dataset.i18n);
      if (value) node.textContent = value;
    });
    $$('[data-i18n-ph]').forEach((node) => { node.placeholder = t(node.dataset.i18nPh); });
    $$('[data-i18n-title]').forEach((node) => {
      node.title = t(node.dataset.i18nTitle);
      node.setAttribute('aria-label', t(node.dataset.i18nTitle));
    });
    $$('.seg--lang button').forEach((button) => {
      button.classList.toggle('is-on', button.dataset.lang === lang());
    });
    $$('#menu-theme button').forEach((button) => {
      button.classList.toggle('is-on', button.dataset.themeOpt === state.prefs.theme);
    });
  }

  function savePrefs() {
    store.set(KEY.prefs, state.prefs);
  }

  /* ── Статус сети ─────────────────────────────────────────────────────── */
  function paintStatus(mode) {
    const node = $('#status');
    const meta = state.meta || {};
    const stamp = (meta.updated_at || '').slice(0, 16);
    if (mode === 'offline') {
      node.hidden = false;
      node.classList.remove('is-live');
      $('#status-text').textContent = stamp ? t('status.offline', { time: stampLabel(stamp) }) : t('status.nocache');
    } else if (mode === 'online') {
      node.hidden = false;
      node.classList.add('is-live');
      $('#status-text').textContent = t('status.online', { time: stampLabel(stamp) || '—' });
      setTimeout(() => { node.hidden = true; }, 4200);
    } else {
      node.hidden = true;
    }
  }

  function toast(text) {
    const node = $('#toast');
    node.textContent = text;
    node.hidden = false;
    clearTimeout(node._timer);
    node._timer = setTimeout(() => { node.hidden = true; }, 2600);
  }

  /* ── Загрузка справочников ───────────────────────────────────────────── */
  async function loadDirectory(force = false) {
    if (!force && state.directory) return state.directory;
    const cached = store.get(KEY.dir);
    if (cached) state.directory = cached;
    if (state.online || force) {
      try {
        const fresh = await api('/api/directory', { timeout: 12000 });
        state.directory = fresh;
        store.set(KEY.dir, fresh);
      } catch (error) { /* остаёмся на кэше */ }
    }
    return state.directory;
  }

  async function refreshMeta() {
    try {
      const fresh = await api('/api/meta');
      if (fresh.now) {
        const serverTime = new Date(fresh.now).getTime();
        if (Number.isFinite(serverTime)) state.drift = serverTime - Date.now();
      }
      state.meta = fresh;
      store.set(KEY.meta, fresh);
    } catch (error) {
      state.meta = state.meta || store.get(KEY.meta) || {};
    }
    return state.meta;
  }

  /* ── Маршрутизация и отрисовка ───────────────────────────────────────── */
  async function render() {
    state.route = parseRoute();
    const { name } = state.route;
    for (const screen of $$('.screen')) screen.hidden = true;
    $('#main').classList.toggle('is-home', name === 'home');
    $$('.nav__links a').forEach((link) => {
      const nav = link.dataset.nav;
      link.classList.toggle('is-on',
        (nav === 'home' && name === 'home') || (name !== 'home' && nav === state.route.kind));
    });

    if (name === 'home') {
      $('#screen-home').hidden = false;
      document.title = 'TTPU · ' + t('brand.sub');
      await loadDirectory();
      renderHome();
    } else if (name === 'browse') {
      $('#screen-browse').hidden = false;
      document.title = t(`browse.${state.route.kind}`) + ' · TTPU';
      await loadDirectory();
      renderBrowse();
    } else {
      $('#screen-schedule').hidden = false;
      await renderSchedule();
    }
    paintLive();
  }

  /* ── События ─────────────────────────────────────────────────────────── */
  function bind() {
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[data-link]');
      if (!link) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      const row = link.closest('.row');
      if (row && row.dataset.kind) {
        remember(row.dataset.kind, row.dataset.id, row.dataset.name);
        saveGroupIfClass(row.dataset.kind, row.dataset.id, row.dataset.name);
      }
      closeSearch();
      closeMenu();
      go(link.getAttribute('href'));
    });

    window.addEventListener('popstate', render);

    $('#btn-search').addEventListener('click', openSearch);
    $('#search-close').addEventListener('click', closeSearch);
    $('#search-overlay').addEventListener('click', (event) => {
      if (event.target === $('#search-overlay')) closeSearch();
    });

    $('#search-input').addEventListener('input', (event) => {
      const value = event.target.value;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => runSearch(value), 180);
    });

    $('#btn-menu').addEventListener('click', () => {
      if ($('#menu-overlay').hidden) openMenu(); else closeMenu();
    });
    $('#menu-close').addEventListener('click', closeMenu);
    $('#menu-overlay').addEventListener('click', (event) => {
      if (event.target === $('#menu-overlay')) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        if (!$('#search-overlay').hidden) closeSearch();
        if (!$('#menu-overlay').hidden) closeMenu();
      }
      if ((event.key === 'k' && (event.metaKey || event.ctrlKey)) ||
          (event.key === '/' && !/input|textarea/i.test(document.activeElement.tagName))) {
        event.preventDefault();
        openSearch();
      }
      if (event.key === 'Enter' && !$('#search-overlay').hidden) {
        const first = $('#search-results .row');
        if (first) first.click();
      }
    });

    $('#btn-theme').addEventListener('click', () => {
      const resolved = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
      state.prefs.theme = resolved === 'dark' ? 'light' : 'dark';
      savePrefs();
      applyTheme();
      paintMenu();
    });

    $$('.seg--lang button').forEach((button) => {
      button.addEventListener('click', () => {
        state.prefs.lang = button.dataset.lang;
        savePrefs();
        applyLang();
        render();
      });
    });

    $('#menu-theme').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-theme-opt]');
      if (!button) return;
      state.prefs.theme = button.dataset.themeOpt;
      savePrefs();
      applyTheme();
      paintMenu();
    });

    $('#browse-tabs').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-kind]');
      if (!button) return;
      go(`/browse/${button.dataset.kind}`);
    });

    $('#browse-input').addEventListener('input', () => paintBrowseList());
    $('#browse-clear').addEventListener('click', () => {
      $('#browse-input').value = '';
      paintBrowseList();
      $('#browse-input').focus();
    });

    $('#view-switch').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-view]');
      if (!button) return;
      setQuery({ view: button.dataset.view, d: null });
    });

    $('#weeknav').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-week-nav]');
      if (!button || button.disabled) return;
      const numbers = Object.keys((state.bundle && state.bundle.weeks) || {});
      const current = pickWeek(state.bundle, state.route.week, isoDate(now()));
      const index = numbers.indexOf(current ? current.tt_num : numbers[0]);
      const target = numbers[index + Number(button.dataset.weekNav)];
      if (target) setQuery({ week: target });
    });

    $('#daytabs').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-day]');
      if (!button) return;
      setQuery({ d: button.dataset.day, view: 'day' });
    });

    $('#schedule-save').addEventListener('click', async () => {
      const { kind, id } = state.route;
      const button = $('#schedule-save');
      try {
        const bundle = await api(`/api/offline/${kind}/${encodeURIComponent(id)}`);
        store.set(KEY.bundle(kind, id), bundle);
        state.bundle = bundle;
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'cache', url: `/api/offline/${kind}/${encodeURIComponent(id)}` });
        }
        button.classList.add('is-done');
        $('#schedule-save-text').textContent = t('sched.saved');
        toast(t('toast.saved'));
      } catch (error) {
        toast(t('status.nocache'));
      }
      paintLive();
    });

    $('#group-change').addEventListener('click', () => go('/browse/class'));

    $('#clear-recent').addEventListener('click', () => {
      store.remove(KEY.recent);
      renderHome();
    });

    $('#finder').addEventListener('submit', (event) => {
      event.preventDefault();
      const value = $('#finder-input').value.trim();
      if (!value) { go('/browse/class'); return; }
      const local = localSearch(value, 8);
      if (local.length) {
        remember(local[0].kind, local[0].id, local[0].name);
        saveGroupIfClass(local[0].kind, local[0].id, local[0].name);
        go(`/${local[0].kind}/${encodeURIComponent(local[0].id)}`);
      } else {
        go(`/browse/class?q=${encodeURIComponent(value)}`);
      }
    });

    $('#finder-input').addEventListener('input', (event) => {
      const value = event.target.value;
      const box = $('#finder-results');
      clearTimeout(finderTimer);
      if (value.trim().length < 2) { box.hidden = true; return; }
      finderTimer = setTimeout(() => {
        const items = localSearch(value, 6);
        if (!items.length) { box.hidden = true; return; }
        box.innerHTML = items.map((item, index) => resultRow(item, index)).join('');
        box.hidden = false;
      }, 140);
    });

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.hero__lead')) $('#finder-results').hidden = true;
    });

    window.addEventListener('online', () => {
      state.online = true;
      paintStatus('online');
      refreshMeta().then(() => { render(); });
    });
    window.addEventListener('offline', () => {
      state.online = false;
      paintStatus('offline');
    });

    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      state.installEvent = event;
      $('#btn-install').hidden = false;
    });
    $('#btn-install').addEventListener('click', async () => {
      if (!state.installEvent) return;
      state.installEvent.prompt();
      await state.installEvent.userChoice;
      state.installEvent = null;
      $('#btn-install').hidden = true;
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (state.prefs.theme === 'auto') applyTheme();
    });

    window.addEventListener('scroll', () => {
      $('#nav').classList.toggle('is-scrolled', window.scrollY > 8);
    }, { passive: true });
  }

  function saveGroupIfClass(kind, id, name) {
    if (kind === 'class') saveGroup(id, name);
  }

  function setQuery(patch) {
    const params = new URLSearchParams(location.search);
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === '' || value === undefined) params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    go(`${location.pathname}${query ? '?' + query : ''}`);
  }

  function openMyDay(offset) {
    const saved = savedGroup();
    if (!saved) { go('/browse/class'); return; }
    const moment = now();
    moment.setDate(moment.getDate() + offset);
    const index = (moment.getDay() + 6) % 7;
    go(`/class/${encodeURIComponent(saved.id)}?view=day&d=${index}`);
  }

  function openMyWeek() {
    const saved = savedGroup();
    if (!saved) { go('/browse/class'); return; }
    go(`/class/${encodeURIComponent(saved.id)}`);
  }

  /* ── Инициализация ───────────────────────────────────────────────────── */
  async function init() {
    const prefs = store.get(KEY.prefs, {});
    state.prefs = { lang: prefs.lang || 'ru', theme: prefs.theme || 'auto' };
    state.meta = store.get(KEY.meta);
    state.directory = store.get(KEY.dir);
    state.online = navigator.onLine;

    applyTheme();
    applyLang();
    bind();
    paintStatus(state.online ? null : 'offline');

    registerWorker();
    startLiveTimer();

    state.route = parseRoute();
    await render();
    refreshMeta().then(() => { if (state.route.name === 'home') renderHome(); });

    if (!state.online && !state.directory) paintStatus('offline');
  }

  function registerWorker() {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => { /* без SW приложение тоже работает */ });
    });
  }

  init();
})();
