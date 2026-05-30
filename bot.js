const fs = require("fs");
const path = require("path");
const http = require("http");

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL || "";
const PORT = Number(process.env.PORT || 8788);
const SELF_TEST = process.argv.includes("--self-test");

const DEFAULT_REMINDER_SLOTS = ["morning", "midday", "evening"];
const REMINDER_HOURS = {
  morning: Number(process.env.REMINDER_MORNING || 9),
  midday: Number(process.env.REMINDER_MIDDAY || 13),
  afternoon: Number(process.env.REMINDER_AFTERNOON || 17),
  evening: Number(process.env.REMINDER_EVENING || 20)
};

const ROOT_DIR = __dirname;
const DATA_DIR = process.env.BOT_DATA_DIR || process.env.DATA_DIR || path.join(ROOT_DIR, "data");
const CONFIG_DIR = process.env.BOT_CONFIG_DIR || path.join(ROOT_DIR, "config");
const STATE_PATH = process.env.BOT_STATE_PATH || path.join(DATA_DIR, "state.json");
const MOTIVATION = loadConfigJson("motivation.json");
const REPLACEMENTS = loadConfigJson("replacements.json");

const HABIT_PRESETS = {
  smoking: {
    type: "smoking",
    name: "Курение",
    emoji: "🚭",
    dailyAmount: 20,
    unitLabel: "сигарет",
    unitCost: 250,
    costLabel: "₽/пачка"
  },
  alcohol: {
    type: "alcohol",
    name: "Алкоголь",
    emoji: "🍷",
    dailyAmount: 1,
    unitLabel: "порций",
    unitCost: 500,
    costLabel: "₽/день"
  }
};

const state = loadState();

if (!BOT_TOKEN && !SELF_TEST) {
  console.error("Missing TELEGRAM_BOT_TOKEN. Create a bot via @BotFather and set the token.");
  process.exit(1);
}

const telegramApi = `https://api.telegram.org/bot${BOT_TOKEN}`;

(SELF_TEST ? runSelfTest() : main()).catch((error) => {
  console.error(error);
  process.exit(1);
});

async function main() {
  startHealthServer();
  startReminderLoop();

  console.log("Habit tracker bot started.");
  let offset = Number(process.env.TELEGRAM_POLLING_OFFSET || 0);

  while (true) {
    try {
      const updates = await telegram("getUpdates", {
        offset,
        timeout: 30,
        allowed_updates: ["message", "callback_query"]
      });

      for (const update of updates.result || []) {
        offset = update.update_id + 1;
        await handleUpdate(update);
      }
    } catch (error) {
      console.error("Polling error:", error.message);
      await wait(1500);
    }
  }
}

async function handleUpdate(update) {
  if (update.callback_query) {
    await handleCallback(update.callback_query);
    return;
  }

  const message = update.message;
  if (!message || !message.chat) return;

  const chatId = message.chat.id;
  const userId = String(message.from?.id || chatId);
  ensureUser(userId, chatId);

  if (!message.text) {
    await sendMessage(chatId, "Пиши текстом или используй кнопки ниже 👇", mainKeyboard());
    return;
  }

  let text = message.text.trim();
  const keyboardMap = {
    "📊 Прогресс": "/stats",
    "💬 Мотивация": "/motivation",
    "🚨 SOS /urge": "/urge",
    "➕ Добавить": "/add",
    "⚙️ Настройки": "/settings",
    "❓ Помощь": "/help"
  };
  if (keyboardMap[text]) text = keyboardMap[text];

  if (text.startsWith("/start")) {
    await sendMessage(chatId, startText(userId), mainKeyboard());
    return;
  }

  if (text.startsWith("/help")) {
    await sendMessage(chatId, helpText(), mainKeyboard());
    return;
  }

  if (text.startsWith("/stats") || text.startsWith("/progress")) {
    await sendMessage(chatId, statsText(userId), statsKeyboard(userId));
    return;
  }

  if (text.startsWith("/motivation") || text.startsWith("/motiv")) {
    await sendMotivation(chatId, userId, "manual");
    return;
  }

  if (text.startsWith("/urge") || text.startsWith("/helpme") || text.startsWith("/sos")) {
    await sendUrgeHelp(chatId, userId);
    return;
  }

  if (text.startsWith("/add")) {
    await sendMessage(chatId, "Выбери, от чего хочешь отказаться:", addHabitKeyboard());
    return;
  }

  if (text.startsWith("/habits")) {
    await sendMessage(chatId, habitsText(userId), habitsKeyboard(userId));
    return;
  }

  if (text.startsWith("/settings")) {
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (text.startsWith("/relapse")) {
    await sendMessage(chatId, relapseIntroText(), relapseKeyboard(userId));
    return;
  }

  if (state.users[userId].awaitingInput) {
    await handleAwaitingInput(userId, chatId, text);
    return;
  }

  await sendMessage(
    chatId,
    "Не понял команду. Нажми кнопку ниже или /help.\n\nЕсли накрыло прямо сейчас — /urge",
    mainKeyboard()
  );
}

async function handleCallback(callback) {
  const data = callback.data || "";
  const chatId = callback.message.chat.id;
  const userId = String(callback.from.id);
  ensureUser(userId, chatId);

  if (data === "menu:main") {
    await answerCallback(callback.id);
    await sendMessage(chatId, startText(userId), mainKeyboard());
    return;
  }

  if (data === "menu:stats") {
    await answerCallback(callback.id);
    await sendMessage(chatId, statsText(userId), statsKeyboard(userId));
    return;
  }

  if (data === "menu:motivation") {
    await answerCallback(callback.id);
    await sendMotivation(chatId, userId, "manual");
    return;
  }

  if (data === "menu:urge") {
    await answerCallback(callback.id);
    await sendUrgeHelp(chatId, userId);
    return;
  }

  if (data === "menu:habits") {
    await answerCallback(callback.id);
    await sendMessage(chatId, habitsText(userId), habitsKeyboard(userId));
    return;
  }

  if (data === "menu:settings") {
    await answerCallback(callback.id);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (data === "add:menu") {
    await answerCallback(callback.id);
    await sendMessage(chatId, "Выбери, от чего хочешь отказаться:", addHabitKeyboard(userId));
    return;
  }

  if (data.startsWith("add:")) {
    const type = data.split(":")[1];
    await answerCallback(callback.id);
    await beginAddHabit(userId, chatId, type);
    return;
  }

  if (data.startsWith("remove:")) {
    const habitId = data.split(":")[1];
    removeHabit(userId, habitId);
    await answerCallback(callback.id, "Привычка удалена");
    await sendMessage(chatId, habitsText(userId), habitsKeyboard(userId));
    return;
  }

  if (data.startsWith("relapse:")) {
    const habitId = data.split(":")[1];
    logRelapse(userId, habitId);
    await answerCallback(callback.id, "Записал. Это не конец пути.");
    await sendMessage(chatId, relapseSupportText(userId, habitId), mainKeyboard());
    return;
  }

  if (data.startsWith("toggle_slot:")) {
    const slot = data.split(":")[1];
    toggleReminderSlot(userId, slot);
    await answerCallback(callback.id);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (data === "toggle_reminders") {
    const user = state.users[userId];
    user.reminders.enabled = !user.reminders.enabled;
    saveState();
    await answerCallback(callback.id);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (data === "replace:more") {
    await answerCallback(callback.id);
    await sendReplacement(chatId, userId);
    return;
  }

  if (data.startsWith("set_tz:")) {
    const offset = Number(data.split(":")[1]);
    state.users[userId].timezoneOffset = offset;
    saveState();
    await answerCallback(callback.id, `Часовой пояс: UTC${offset >= 0 ? "+" : ""}${offset}`);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  await answerCallback(callback.id);
}

async function handleAwaitingInput(userId, chatId, text) {
  const pending = state.users[userId].awaitingInput;
  if (!pending) return;

  if (pending.type === "custom_habit_name") {
    const name = cleanText(text).slice(0, 40);
    if (!name) {
      await sendMessage(chatId, "Напиши название привычки текстом.");
      return;
    }
    state.users[userId].awaitingInput = { type: "custom_daily_amount", name };
    saveState();
    await sendMessage(chatId, `Сколько раз в день обычно? (число, например 5)\nИли напиши 0, если не считаешь.`);
    return;
  }

  if (pending.type === "custom_daily_amount") {
    const dailyAmount = Math.max(0, Number(text.replace(",", ".")) || 0);
    state.users[userId].awaitingInput = { type: "custom_unit_cost", name: pending.name, dailyAmount };
    saveState();
    await sendMessage(chatId, "Сколько ₽ тратишь в день на эту привычку? (число, или 0)");
    return;
  }

  if (pending.type === "custom_unit_cost") {
    const unitCost = Math.max(0, Number(text.replace(",", ".")) || 0);
    addHabit(userId, {
      type: "custom",
      name: pending.name,
      emoji: "🎯",
      dailyAmount: pending.dailyAmount,
      unitCost,
      unitLabel: "раз",
      costLabel: "₽/день"
    });
    state.users[userId].awaitingInput = null;
    saveState();
    await sendMessage(chatId, `✅ Добавлено: ${pending.name}\n\n${statsText(userId)}`, mainKeyboard());
    return;
  }

  if (pending.type === "preset_daily_amount") {
    const normalized = text.toLowerCase();
    const parsed = Number(text.replace(",", "."));
    const dailyAmount = normalized === "ок" || normalized === "ok"
      ? pending.defaultAmount
      : Math.max(1, parsed || pending.defaultAmount);
    addHabit(userId, {
      ...HABIT_PRESETS[pending.presetType],
      dailyAmount
    });
    state.users[userId].awaitingInput = null;
    saveState();
    const preset = HABIT_PRESETS[pending.presetType];
    await sendMessage(
      chatId,
      `✅ Отслеживаем: ${preset.emoji} ${preset.name}\nСтарт: сегодня\n\n${pickMotivation(preset.type, "morning", getHabitByType(userId, preset.type), state.users[userId].timezoneOffset)}`,
      mainKeyboard()
    );
    return;
  }

  state.users[userId].awaitingInput = null;
  saveState();
}

async function beginAddHabit(userId, chatId, type) {
  if (type === "custom") {
    state.users[userId].awaitingInput = { type: "custom_habit_name" };
    saveState();
    await sendMessage(chatId, "Напиши название привычки, от которой отказываешься.\nНапример: сладкое, соцсети, азартные игры.");
    return;
  }

  const preset = HABIT_PRESETS[type];
  if (!preset) {
    await sendMessage(chatId, "Неизвестный тип. Выбери из списка.", addHabitKeyboard(userId));
    return;
  }

  if (getHabitByType(userId, type)) {
    await sendMessage(chatId, `${preset.emoji} ${preset.name} уже добавлено. Смотри /stats`, mainKeyboard());
    return;
  }

  state.users[userId].awaitingInput = {
    type: "preset_daily_amount",
    presetType: type,
    defaultAmount: preset.dailyAmount
  };
  saveState();
  await sendMessage(
    chatId,
    `${preset.emoji} ${preset.name}\n\nСколько ${preset.unitLabel} в день обычно? (по умолчанию ${preset.dailyAmount})\nНапиши число или «ок» для значения по умолчанию.`
  );
}

function addHabit(userId, config) {
  ensureUser(userId);
  const user = state.users[userId];
  const id = config.type === "custom" ? `custom-${Date.now()}` : config.type;
  user.habits.push({
    id,
    type: config.type,
    name: config.name,
    emoji: config.emoji || "🎯",
    quitDate: todayKey(user.timezoneOffset),
    dailyAmount: config.dailyAmount || 1,
    unitCost: config.unitCost ?? HABIT_PRESETS[config.type]?.unitCost ?? 0,
    unitLabel: config.unitLabel || HABIT_PRESETS[config.type]?.unitLabel || "раз",
    relapses: [],
    lastMotivationSlot: {}
  });
  saveState();
}

function removeHabit(userId, habitId) {
  const user = state.users[userId];
  user.habits = user.habits.filter((habit) => habit.id !== habitId);
  saveState();
}

function logRelapse(userId, habitId) {
  const habit = getHabit(userId, habitId);
  if (!habit) return;
  habit.relapses.push({ at: new Date().toISOString() });
  habit.quitDate = todayKey(state.users[userId].timezoneOffset);
  saveState();
}

function toggleReminderSlot(userId, slot) {
  const user = state.users[userId];
  const index = user.reminders.slots.indexOf(slot);
  if (index >= 0) user.reminders.slots.splice(index, 1);
  else user.reminders.slots.push(slot);
  user.reminders.slots.sort();
  saveState();
}

async function sendMotivation(chatId, userId, source) {
  const user = state.users[userId];
  if (!user.habits.length) {
    await sendMessage(chatId, "Сначала добавь привычку для отслеживания.", addHabitKeyboard(userId));
    return;
  }

  const habit = pickRandom(user.habits);
  const slot = source === "manual" ? currentSlot(user.timezoneOffset) : source;
  const text = pickMotivation(habit.type, slot, habit, user.timezoneOffset);
  await sendMessage(chatId, `${habit.emoji} ${habit.name}\n\n${text}`, mainKeyboard());
}

async function sendUrgeHelp(chatId, userId) {
  const user = state.users[userId];
  const habit = user.habits.length ? pickRandom(user.habits) : null;
  const motivation = habit
    ? pickMotivation(habit.type, "urge", habit, user.timezoneOffset)
    : pickFrom(MOTIVATION.general.urge);
  const replacement = pickReplacement(habit?.type || "general");

  await sendMessage(
    chatId,
    `🚨 **Сильное желание — это нормально.**\n\n${motivation}\n\n🔄 **Замени привычку на:**\n${replacement}`,
    {
      inline_keyboard: [
        [{ text: "🔄 Ещё замена", callback_data: "replace:more" }],
        [{ text: "📊 Мой прогресс", callback_data: "menu:stats" }],
        [{ text: "💬 Ещё мотивация", callback_data: "menu:motivation" }]
      ]
    }
  );
}

async function sendReplacement(chatId, userId) {
  const user = state.users[userId];
  const habit = user.habits.length ? pickRandom(user.habits) : null;
  const replacement = pickReplacement(habit?.type || "general");
  await sendMessage(chatId, `🔄 Попробуй вместо этого:\n\n${replacement}`, {
    inline_keyboard: [[{ text: "🔄 Ещё идея", callback_data: "replace:more" }]]
  });
}

function pickMotivation(habitType, slot, habit, timezoneOffset = 3) {
  const pool = [
    ...asArray(MOTIVATION[habitType]?.[slot]),
    ...asArray(MOTIVATION.general[slot]),
    ...asArray(MOTIVATION[habitType]?.urge),
    ...asArray(MOTIVATION.general.urge)
  ].filter(Boolean);

  let message = pickRandom(pool.length ? pool : ["💪 Ты держишься. Это главное."]);
  const stats = habitStats(habit, timezoneOffset);

  message = message
    .replaceAll("{days}", String(stats.days))
    .replaceAll("{savedMoney}", String(stats.savedMoney))
    .replaceAll("{savedUnits}", String(stats.savedUnits));

  const milestone = MOTIVATION[habitType]?.milestones?.[String(stats.days)];
  if (milestone) message = `${milestone}\n\n${message}`;

  return message;
}

function pickReplacement(habitType) {
  const pool = [
    ...asArray(REPLACEMENTS[habitType]),
    ...asArray(REPLACEMENTS.general)
  ];
  return pickRandom(pool);
}

function statsText(userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    return "Пока нет отслеживаемых привычек.\n\nДобавь курение, алкоголь или свою — и я буду считать дни и присылать мотивацию.";
  }

  return user.habits
    .map((habit) => {
      const stats = habitStats(habit, user.timezoneOffset);
      return [
        `${habit.emoji} **${habit.name}**`,
        `📅 Без срыва: **${stats.days}** ${pluralDays(stats.days)}`,
        `🔥 Текущий streak: **${stats.currentStreak}** ${pluralDays(stats.currentStreak)}`,
        `🏆 Лучший streak: **${stats.bestStreak}** ${pluralDays(stats.bestStreak)}`,
        stats.savedUnits > 0 ? `📉 Не потреблено: ~**${stats.savedUnits}** ${habit.unitLabel}` : null,
        stats.savedMoney > 0 ? `💰 Сэкономлено: ~**${stats.savedMoney} ₽**` : null,
        stats.relapseCount > 0 ? `⚠️ Срывов записано: ${stats.relapseCount}` : null,
        `🗓 Старт текущего цикла: ${formatDate(habit.quitDate)}`
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n");
}

function habitStats(habit, timezoneOffset = 3) {
  const days = daysSince(habit.quitDate, timezoneOffset);
  const savedUnits = Math.round(days * (habit.dailyAmount || 0));
  const savedMoney = estimateSavedMoney(habit, days);
  const relapseCount = habit.relapses?.length || 0;
  const currentStreak = days;
  const bestStreak = Math.max(currentStreak, habit.bestStreak || 0);

  if (bestStreak > (habit.bestStreak || 0)) {
    habit.bestStreak = bestStreak;
    saveState();
  }

  return { days, savedUnits, savedMoney, relapseCount, currentStreak, bestStreak };
}

function estimateSavedMoney(habit, days) {
  if (!habit.unitCost) return 0;
  if (habit.type === "smoking") {
    const packs = (days * (habit.dailyAmount || 20)) / 20;
    return Math.round(packs * habit.unitCost);
  }
  return Math.round(days * habit.unitCost);
}

function habitsText(userId) {
  const user = state.users[userId];
  if (!user.habits.length) return "Список пуст. Добавь первую привычку 👇";
  return user.habits
    .map((habit) => {
      const stats = habitStats(habit, user.timezoneOffset);
      return `${habit.emoji} ${habit.name} — ${stats.days} ${pluralDays(stats.days)}`;
    })
    .join("\n");
}

function settingsText(userId) {
  const user = state.users[userId];
  const slots = user.reminders.slots.length
    ? user.reminders.slots.map(slotLabel).join(", ")
    : "выключены";
  return [
    "⚙️ **Настройки**",
    `🔔 Напоминания: ${user.reminders.enabled ? "включены" : "выключены"}`,
    `🕐 Слоты: ${slots}`,
    `🌍 Часовой пояс: UTC${user.timezoneOffset >= 0 ? "+" : ""}${user.timezoneOffset}`,
    "",
    "Напоминания приходят 1 раз в выбранный слот, если ещё не отправляли сегодня."
  ].join("\n");
}

function startText(userId) {
  const user = state.users[userId];
  const intro = [
    "💚 **Habit Tracker — твой путь без вредных привычек**",
    "",
    "Я помогаю отказаться от **курения**, **алкоголя** и других привычек:",
    "• считаю дни и streak",
    "• присылаю мотивацию утром, днём и вечером",
    "• помогаю в момент сильного желания (/urge)",
    "• предлагаю **здоровые замены**",
    "",
    "⚠️ Я не заменяю врача. При тяжёой зависимости — обратись к специалисту."
  ];

  if (user.habits.length) intro.push("", statsText(userId));
  else intro.push("", "Начни с добавления привычки 👇");

  return intro.join("\n");
}

function helpText() {
  return [
    "📖 **Команды**",
    "/start — главное меню",
    "/stats — прогресс и streak",
    "/motivation — мотивация сейчас",
    "/urge — сильное желание, SOS-помощь",
    "/habits — список привычек",
    "/relapse — честно записать срыв",
    "/settings — напоминания и часовой пояс",
    "/help — эта справка",
    "",
    "Кнопка **SOS** — когда накрывает прямо сейчас."
  ].join("\n");
}

function relapseIntroText() {
  return "⚠️ Срыв случается. Это не конец пути.\n\nВыбери привычку — я запишу и помогу вернуться в строй. Streak начнётся заново, но опыт останется.";
}

function relapseSupportText(userId, habitId) {
  const habit = getHabit(userId, habitId);
  if (!habit) return "Записал. Дыши. Ты можешь начать снова прямо сейчас.";
  return [
    `${habit.emoji} **${habit.name}** — срыв записан.`,
    "",
    pickMotivation(habit.type, "urge", habit, state.users[userId].timezoneOffset),
    "",
    "🔄 Новый цикл начался сегодня. Один срыв не определяет тебя."
  ].join("\n");
}

function mainKeyboard() {
  return {
    keyboard: [
      [{ text: "📊 Прогресс" }, { text: "💬 Мотивация" }],
      [{ text: "🚨 SOS /urge" }, { text: "➕ Добавить" }],
      [{ text: "⚙️ Настройки" }, { text: "❓ Помощь" }]
    ],
    resize_keyboard: true
  };
}

function statsKeyboard(userId) {
  return {
    inline_keyboard: [
      [{ text: "💬 Мотивация", callback_data: "menu:motivation" }],
      [{ text: "🚨 SOS", callback_data: "menu:urge" }],
      [{ text: "➕ Добавить привычку", callback_data: "add:menu" }]
    ]
  };
}

function habitsKeyboard(userId) {
  const user = state.users[userId];
  const rows = user.habits.map((habit) => [
    { text: `🗑 ${habit.emoji} ${habit.name}`, callback_data: `remove:${habit.id}` }
  ]);
  rows.push([{ text: "➕ Добавить", callback_data: "add:menu" }]);
  return { inline_keyboard: rows };
}

function addHabitKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "🚭 Курение", callback_data: "add:smoking" }],
      [{ text: "🍷 Алкоголь", callback_data: "add:alcohol" }],
      [{ text: "🎯 Своя привычка", callback_data: "add:custom" }]
    ]
  };
}

function settingsKeyboard(userId) {
  const user = state.users[userId];
  const slots = ["morning", "midday", "afternoon", "evening"];
  const slotRows = slots.map((slot) => [{
    text: `${user.reminders.slots.includes(slot) ? "✅" : "⬜"} ${slotLabel(slot)}`,
    callback_data: `toggle_slot:${slot}`
  }]);

  return {
    inline_keyboard: [
      [{ text: user.reminders.enabled ? "🔔 Выключить напоминания" : "🔕 Включить напоминания", callback_data: "toggle_reminders" }],
      ...slotRows,
      [
        { text: "UTC+2", callback_data: "set_tz:2" },
        { text: "UTC+3", callback_data: "set_tz:3" },
        { text: "UTC+4", callback_data: "set_tz:4" }
      ],
      [{ text: "← Назад", callback_data: "menu:main" }]
    ]
  };
}

function relapseKeyboard(userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    return { inline_keyboard: [[{ text: "➕ Добавить привычку", callback_data: "add:menu" }]] };
  }
  return {
    inline_keyboard: user.habits.map((habit) => [
      { text: `${habit.emoji} ${habit.name}`, callback_data: `relapse:${habit.id}` }
    ])
  };
}

function startReminderLoop() {
  setInterval(() => {
    tickReminders().catch((error) => console.error("Reminder loop:", error.message));
  }, 60 * 1000);
  tickReminders().catch((error) => console.error("Reminder loop:", error.message));
}

async function tickReminders() {
  for (const [userId, user] of Object.entries(state.users)) {
    if (!user.reminders?.enabled || !user.chatId || !user.habits.length) continue;

    const hour = currentHour(user.timezoneOffset);
    for (const slot of user.reminders.slots || DEFAULT_REMINDER_SLOTS) {
      if (hour !== REMINDER_HOURS[slot]) continue;
      if (user.lastReminderDate?.[slot] === todayKey(user.timezoneOffset)) continue;

      user.lastReminderDate = user.lastReminderDate || {};
      user.lastReminderDate[slot] = todayKey(user.timezoneOffset);
      saveState();

      const habit = pickRandom(user.habits);
      const text = pickMotivation(habit.type, slot, habit, user.timezoneOffset);
      try {
        await sendMessage(
          user.chatId,
          `🔔 ${slotLabel(slot)}\n\n${habit.emoji} ${habit.name}\n\n${text}`,
          mainKeyboard()
        );
      } catch (error) {
        console.error(`Reminder failed for ${userId}:`, error.message);
      }
    }
  }
}

function startHealthServer() {
  http
    .createServer((req, res) => {
      res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Habit tracker bot is running.");
    })
    .listen(PORT, () => console.log(`Health server listening on ${PORT}`));
}

async function telegram(method, payload) {
  const response = await fetch(`${telegramApi}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!data.ok) throw new Error(`${method}: ${data.description || response.statusText}`);
  return data;
}

async function sendMessage(chatId, text, replyMarkup) {
  return telegram("sendMessage", {
    chat_id: chatId,
    text,
    parse_mode: "Markdown",
    disable_web_page_preview: true,
    reply_markup: replyMarkup
  });
}

async function answerCallback(callbackQueryId, text) {
  return telegram("answerCallbackQuery", {
    callback_query_id: callbackQueryId,
    text: text || "",
    show_alert: Boolean(text)
  });
}

function ensureUser(userId, chatId) {
  if (!state.users[userId]) {
    state.users[userId] = {
      chatId: chatId || null,
      timezoneOffset: 3,
      habits: [],
      reminders: { enabled: true, slots: [...DEFAULT_REMINDER_SLOTS] },
      lastReminderDate: {},
      awaitingInput: null,
      createdAt: new Date().toISOString()
    };
  }
  if (chatId) state.users[userId].chatId = chatId;
}

function getHabit(userId, habitId) {
  return state.users[userId]?.habits.find((habit) => habit.id === habitId);
}

function getHabitByType(userId, type) {
  return state.users[userId]?.habits.find((habit) => habit.type === type);
}

function loadState() {
  if (!fs.existsSync(STATE_PATH)) return { users: {} };
  try {
    const parsed = JSON.parse(fs.readFileSync(STATE_PATH, "utf8"));
    return { users: parsed.users || {} };
  } catch {
    return { users: {} };
  }
}

function saveState() {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function loadConfigJson(name) {
  const candidates = [
    path.join(CONFIG_DIR, name),
    path.join(ROOT_DIR, "data", name)
  ];
  for (const filePath of candidates) {
    if (fs.existsSync(filePath)) return loadJson(filePath);
  }
  throw new Error(`Missing config file: ${name}`);
}

function todayKey(timezoneOffset = 3) {
  const now = new Date(Date.now() + timezoneOffset * 3600000);
  return now.toISOString().slice(0, 10);
}

function daysSince(dateKey, timezoneOffset = 3) {
  if (!dateKey) return 0;
  const start = new Date(`${dateKey}T00:00:00.000Z`);
  const now = new Date(Date.now() + timezoneOffset * 3600000);
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const diff = today - start;
  return Math.max(0, Math.floor(diff / 86400000));
}

function currentHour(timezoneOffset = 3) {
  const now = new Date(Date.now() + timezoneOffset * 3600000);
  return now.getUTCHours();
}

function currentSlot(timezoneOffset = 3) {
  const hour = currentHour(timezoneOffset);
  if (hour >= 7 && hour <= 10) return "morning";
  if (hour >= 11 && hour <= 14) return "midday";
  if (hour >= 15 && hour <= 18) return "afternoon";
  return "evening";
}

function slotLabel(slot) {
  return {
    morning: "Утро",
    midday: "День",
    afternoon: "После обеда",
    evening: "Вечер"
  }[slot] || slot;
}

function formatDate(dateKey) {
  const [y, m, d] = dateKey.split("-");
  return `${d}.${m}.${y}`;
}

function pluralDays(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "дня";
  return "дней";
}

function pickRandom(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function pickFrom(list) {
  return pickRandom(list);
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  return [value];
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runSelfTest() {
  ensureUser("test", 1);
  addHabit("test", { ...HABIT_PRESETS.smoking, dailyAmount: 15 });
  const user = state.users.test;
  const habit = user.habits[0];
  console.log("Stats:\n", statsText("test"));
  console.log("\nMotivation morning:\n", pickMotivation("smoking", "morning", habit, 3));
  console.log("\nUrge:\n", pickMotivation("smoking", "urge", habit, 3));
  console.log("\nReplacement:\n", pickReplacement("smoking"));
  console.log("\nSelf-test OK");
}
