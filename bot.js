const fs = require("fs");
const path = require("path");
const http = require("http");

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL || "";
const PORT = Number(process.env.PORT || 8788);
const RADIO_GRAM_URL = process.env.RADIO_GRAM_URL || "https://player.radiogram.su/";
const CHANNEL_URL = process.env.CHANNEL_URL || "https://t.me/gramradiochill";
const SUPPORT_URL = process.env.SUPPORT_URL || "https://pay.cloudtips.ru/p/b5dba7c2";
const TON_WALLET = process.env.TON_WALLET || "UQDNJZb6MPyqP1P1JONmZ5Que0_UMA1n4k3ugAYcVEv7XH3Q";
const ADMIN_CHAT_ID = process.env.ADMIN_CHAT_ID || "2010814946";
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
const ARTICLES = loadConfigJson("articles.json");
const IMAGES_META = loadConfigJson("images.json");
const SAVINGS_IDEAS = loadConfigJson("savings-ideas.json");
const PLAYLISTS = loadConfigJson("playlists.json");
const IMAGES_DIR = path.join(CONFIG_DIR, "images");
const EXTRAS = require("./lib/extras");
const ADMIN = require("./lib/admin-stats");
const GAMIFICATION = require("./lib/gamification");
const VISUAL = require("./lib/visual");
const TONES = require("./lib/tones");
const { supportKeyboard, moodKeyboard, proText } = require("./lib/bot-helpers");
const METRICS = require("./lib/habit-metrics");

const HABIT_PRESETS = {
  smoking: {
    type: "smoking",
    name: "Курение",
    emoji: "🚭",
    dailyAmount: 20,
    unitLabel: "сигарет",
    unitCost: 250,
    moneyPerDay: 250,
    costLabel: "₽/пачка"
  },
  alcohol: {
    type: "alcohol",
    name: "Алкоголь",
    emoji: "🍷",
    dailyAmount: 1,
    unitLabel: "порций",
    unitCost: 500,
    moneyPerDay: 500,
    costLabel: "₽/день"
  },
  masturbation: {
    type: "masturbation",
    name: "Онанизм / порно",
    emoji: "🧠",
    trackMode: "time",
    dailyAmount: 1,
    unitLabel: "раз",
    minutesPerDay: 30,
    unitCost: 0,
    moneyPerDay: 0,
    costLabel: "мин/день"
  },
  junkfood: {
    type: "junkfood",
    name: "Питание / похудение",
    emoji: "🍔",
    trackMode: "weight",
    dailyAmount: 0,
    unitLabel: "кг",
    unitCost: 0,
    moneyPerDay: 0,
    costLabel: "кг"
  }
};

const state = loadState();

if (!BOT_TOKEN && !SELF_TEST) {
  console.error("Missing TELEGRAM_BOT_TOKEN. Create a bot via @BotFather and set the token.");
  process.exit(1);
}

assertDeployFiles();

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
  touchUser(userId, chatId);

  if (!message.text) {
    await sendMessage(chatId, "Пиши текстом или используй кнопки ниже 👇", mainKeyboard());
    return;
  }

  let text = message.text.trim();
  const keyboardMap = {
    "📊 Прогресс": "/stats",
    "💬 Мотивация": "/motivation",
    "🚨 SOS /urge": "/urge",
    "😔 Сорвался": "/relapse",
    "📚 Статьи": "/articles",
    "➕ Добавить": "/add",
    "🗑 Удалить": "/delete",
    "🎧 Радио & музыка": "/links",
    "⚙️ Настройки": "/settings",
    "📅 Календарь": "/calendar",
    "🎲 Удача": "/luck",
    "☕ Поддержать": "/support",
    "❓ Помощь": "/help"
  };
  if (keyboardMap[text]) text = keyboardMap[text];

  if (text.startsWith("/start")) {
    const payload = text.split(/\s+/)[1];
    if (payload?.startsWith("ch_")) {
      const linked = linkChallengeBuddy(userId, payload.slice(3));
      if (linked) {
        await sendMessage(chatId, "👥 **Челлендж подключён!** Сравнивай streak: /buddy");
      }
    }
    if (payload?.startsWith("ref_")) {
      const refId = payload.slice(4);
      if (refId && refId !== userId && state.users[refId]) {
        state.users[refId].referralCount = Math.min(2, (state.users[refId].referralCount || 0) + 1);
        saveState();
        await sendMessage(chatId, "🎁 Спасибо другу! У него +1 заморозка streak в месяц.");
      }
    }
    await sendMessage(chatId, startText(userId), mainKeyboard());
    await sendMessage(chatId, linksIntroText(), linksKeyboard());
    return;
  }

  if (text.startsWith("/help")) {
    await sendMessage(chatId, helpText(), mainKeyboard());
    return;
  }

  if (text.startsWith("/stats") || text.startsWith("/progress")) {
    await sendStatsWithImages(chatId, userId);
    return;
  }

  if (text.startsWith("/weight")) {
    const arg = text.replace(/^\/weight\s*/i, "").trim().replace(",", ".");
    const kg = Number(arg);
    const user = state.users[userId];
    const weightHabits = (user.habits || []).filter((h) => METRICS.isWeightHabit(h));
    if (!weightHabits.length) {
      await sendMessage(chatId, "Сначала добавь привычку **Питание / похудение**.", addHabitKeyboard(userId));
      return;
    }
    if (!arg || !Number.isFinite(kg) || kg < 30 || kg > 300) {
      await sendMessage(chatId, "⚖️ Напиши: `/weight 75.5` — твой текущий вес в кг.", mainKeyboard());
      return;
    }
    for (const h of weightHabits) {
      if (h.startWeightKg == null) h.startWeightKg = kg;
      h.currentWeightKg = Math.round(kg * 10) / 10;
    }
    saveState();
    await sendStatsWithImages(chatId, userId);
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
    await sendMessage(chatId, "Выбери, от чего хочешь отказаться:\n\n⚡ — быстрый старт с настройками по умолчанию", addHabitKeyboard(userId));
    return;
  }

  if (text.startsWith("/habits") || text.startsWith("/delete") || text.startsWith("/remove")) {
    const intro = text.startsWith("/delete") || text.startsWith("/remove")
      ? deleteHabitIntroText()
      : habitsText(userId);
    await sendMessage(chatId, intro, habitsKeyboard(userId));
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

  if (text.startsWith("/articles") || text.startsWith("/article")) {
    await sendMessage(chatId, articlesIntroText(), articlesMenuKeyboard(userId));
    return;
  }

  if (text.startsWith("/links") || text.startsWith("/radio")) {
    await sendMessage(chatId, linksIntroText(), linksKeyboard());
    return;
  }

  if (text.startsWith("/edit")) {
    await sendMessage(chatId, "✏️ Выбери привычку — изменю **₽/день**:", editHabitKeyboard(userId));
    return;
  }

  if (text.startsWith("/goal")) {
    state.users[userId].awaitingInput = { type: "savings_goal_title" };
    saveState();
    await sendMessage(chatId, "🎯 **На что копишь?**\nНапример: новые наушники, отпуск, курс\n\nНапиши название цели:");
    return;
  }

  if (text.startsWith("/spent")) {
    state.users[userId].awaitingInput = { type: "spent_saved_amount" };
    saveState();
    await sendMessage(chatId, "💸 **Потратил сэкономленное?**\nНапиши сумму в ₽ (я вычту из цели):");
    return;
  }

  if (text.startsWith("/share")) {
    await sendShareMenu(chatId, userId);
    return;
  }

  if (text.startsWith("/freeze")) {
    await useStreakFreeze(chatId, userId);
    return;
  }

  if (text.startsWith("/buddy")) {
    await sendMessage(chatId, buddyText(userId), mainKeyboard());
    return;
  }

  if (text.startsWith("/challenge")) {
    const arg = text.split(/\s+/)[1];
    if (arg) {
      const linked = linkChallengeBuddy(userId, arg.toUpperCase());
      await sendMessage(
        chatId,
        linked ? "👥 **Друг подключён!** /buddy — сравнение streak" : "Код не найден. Попроси друга прислать свой /challenge",
        mainKeyboard()
      );
    } else {
      const code = ensureChallengeCode(state.users[userId]);
      saveState();
      await sendMessage(
        chatId,
        `👥 **Челлендж с другом**\n\nТвой код: \`${code}\`\n\nДруг пишет:\n/challenge ${code}\n\nРеферал (+заморозка):\n\`?start=ref_${userId}\``,
        mainKeyboard()
      );
    }
    return;
  }

  if (text.startsWith("/adminstats")) {
    if (!ADMIN.isAdmin(userId, ADMIN_CHAT_ID)) return;
    await sendMessage(chatId, adminStatsText());
    return;
  }

  if (text.startsWith("/calendar")) {
    const days = GAMIFICATION.isPro(state.users[userId]) ? 30 : 14;
    await sendMessage(chatId, GAMIFICATION.calendarText(state.users[userId], (h) => habitStats(h, state.users[userId].timezoneOffset), state.users[userId].timezoneOffset, days), mainKeyboard());
    return;
  }

  if (text.startsWith("/luck")) {
    await sendDailyLuck(chatId, userId);
    return;
  }

  if (text.startsWith("/vacation")) {
    GAMIFICATION.startVacation(state.users[userId], 3);
    saveState();
    await sendMessage(chatId, "🏖 **Режим отдыха 3 дня**\n\nБез упреков. Напоминания мягче. Streak на месте.\n\n/urge и SOS — как обычно.", mainKeyboard());
    return;
  }

  if (text.startsWith("/pro")) {
    await sendMessage(chatId, proText(state.users[userId], GAMIFICATION.isPro), mainKeyboard());
    return;
  }

  if (text.startsWith("/support") || text.startsWith("/donate")) {
    await sendSupportMenu(chatId);
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
  touchUser(userId, chatId);

  if (data === "menu:links") {
    await answerCallback(callback.id);
    await sendMessage(chatId, linksIntroText(), linksKeyboard());
    return;
  }

  if (data === "menu:main") {
    await answerCallback(callback.id);
    await sendMessage(chatId, startText(userId), mainKeyboard());
    return;
  }

  if (data === "menu:stats") {
    await answerCallback(callback.id);
    await sendStatsWithImages(chatId, userId);
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

  if (data === "menu:relapse") {
    await answerCallback(callback.id);
    await sendMessage(chatId, relapseIntroText(), relapseKeyboard(userId));
    return;
  }

  if (data === "add:menu") {
    await answerCallback(callback.id);
    await sendMessage(chatId, "Выбери, от чего хочешь отказаться:", addHabitKeyboard(userId));
    return;
  }

  if (data.startsWith("add:")) {
    const parts = data.split(":");
    const type = parts[1] === "quick" ? parts[2] : parts[1];
    await answerCallback(callback.id);
    if (parts[1] === "quick") {
      await beginQuickAddHabit(userId, chatId, type);
      return;
    }
    await beginAddHabit(userId, chatId, type);
    return;
  }

  if (data.startsWith("edit:")) {
    const habitId = data.split(":")[1];
    if (habitId === "menu") {
      await answerCallback(callback.id);
      await sendMessage(chatId, "✏️ Выбери привычку:", editHabitKeyboard(userId));
      return;
    }
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) return;
    if (METRICS.isTimeHabit(habit)) {
      state.users[userId].awaitingInput = { type: "edit_minutes", habitId };
      saveState();
      await sendMessage(
        chatId,
        `${habit.emoji} **${habit.name}**\n\nСейчас **${METRICS.getMinutesPerDay(habit)} мин/день**.\nНапиши новое число минут:`
      );
      return;
    }
    if (METRICS.isWeightHabit(habit)) {
      state.users[userId].awaitingInput = { type: "edit_weight", habitId };
      saveState();
      const wp = METRICS.weightProgress(habit);
      await sendMessage(
        chatId,
        `${habit.emoji} **${habit.name}**\n\nВес: **${wp?.current ?? "—"}** кг · цель **${wp?.target ?? "—"}** кг\n\nНапиши: \`текущий цель\` (например \`78 72\`) или только вес: \`78\``
      );
      return;
    }
    state.users[userId].awaitingInput = { type: "edit_money", habitId };
    saveState();
    await sendMessage(
      chatId,
      `${habit.emoji} **${habit.name}**\n\nСейчас **${getMoneyPerDay(habit)} ₽/день**.\nНапиши новую сумму:`
    );
    return;
  }

  if (data.startsWith("share:")) {
    const habitId = data.split(":")[1];
    if (habitId === "menu") {
      await answerCallback(callback.id);
      await sendShareMenu(chatId, userId);
      return;
    }
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) return;
    const stats = habitStats(habit, state.users[userId].timezoneOffset);
    const cap = `${shareStreakCard(habit, stats)}\n\n_Перешли другу — это победа._`;
    await sendBannerBuffer(chatId, "share", cap, mainKeyboard());
    return;
  }

  if (data.startsWith("trigger:")) {
    const [, habitId, triggerId] = data.split(":");
    const habit = getHabit(userId, habitId);
    if (habit?.relapses?.length) {
      habit.relapses[habit.relapses.length - 1].trigger = triggerId;
      saveState();
    }
    await answerCallback(callback.id, "Записал");
    await sendMessage(chatId, "Спасибо за честность — это поможет заметить паттерн.", mainKeyboard());
    return;
  }

  if (data === "timer:start") {
    const user = state.users[userId];
    const habit = user.habits.length ? pickRandom(user.habits) : null;
    user.activeTimer = {
      habitId: habit?.id || null,
      endsAt: Date.now() + 10 * 60 * 1000
    };
    saveState();
    await answerCallback(callback.id, "10 минут");
    const playlist = pickPlaylist(habit?.type || "general", "urge");
    await sendBannerBuffer(
      chatId,
      "sos",
      `⏱ **10 минут без решений**\n\n_${TONES.pickTone("sos")}_\n\n📻 ${playlist.label}`,
      {
        inline_keyboard: [[{ text: playlist.label, url: playlist.url }]]
      }
    );
    await sendMessage(
      chatId,
      "Желание часто проходит за это время. Дыши, включи музыку.\n\nНапишу, когда время выйдет — спрошу «как сейчас?»",
      mainKeyboard()
    );
    return;
  }

  if (data === "freeze:use") {
    await answerCallback(callback.id);
    await useStreakFreeze(chatId, userId);
    return;
  }

  if (data === "toggle_quiet") {
    const user = state.users[userId];
    user.quietHours = user.quietHours || { enabled: false, start: 23, end: 8 };
    user.quietHours.enabled = !user.quietHours.enabled;
    saveState();
    await answerCallback(callback.id);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (data === "toggle_digest") {
    const user = state.users[userId];
    user.digestEvening = user.digestEvening === false;
    saveState();
    await answerCallback(callback.id);
    await sendMessage(chatId, settingsText(userId), settingsKeyboard(userId));
    return;
  }

  if (data.startsWith("mood:")) {
    const mood = data.split(":")[1];
    GAMIFICATION.recordMood(state.users[userId], mood);
    saveState();
    await answerCallback(callback.id, "Спасибо");
    const stat = GAMIFICATION.moodStats(state.users[userId]);
    await sendMessage(chatId, stat ? `${stat}\n\n_Данные помогают видеть прогресс._` : "Записал.", mainKeyboard());
    return;
  }

  if (data === "menu:support") {
    await answerCallback(callback.id);
    await sendSupportMenu(chatId);
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

  if (data.startsWith("remove:") && data.split(":").length === 2) {
    const habitId = data.split(":")[1];
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) {
      await sendMessage(chatId, "Привычка не найдена.", habitsKeyboard(userId));
      return;
    }
    await sendMessage(
      chatId,
      `🗑 **Удалить привычку?**\n\n${habit.emoji} **${habit.name}**\n\nСтатистика и streak по ней **исчезнут**. Это нельзя отменить.`,
      deleteConfirmKeyboard(habitId)
    );
    return;
  }

  if (data.startsWith("remove:confirm:")) {
    const habitId = data.split(":")[2];
    const habit = getHabit(userId, habitId);
    const name = habit ? `${habit.emoji} ${habit.name}` : "Привычка";
    removeHabit(userId, habitId);
    await answerCallback(callback.id, "Удалено");
    await sendMessage(chatId, `✅ ${name} удалена из трекера.`, mainKeyboard());
    return;
  }

  if (data === "article:menu") {
    await answerCallback(callback.id);
    await sendMessage(chatId, articlesIntroText(), articlesMenuKeyboard(userId));
    return;
  }

  if (data.startsWith("article:pick:")) {
    const habitId = data.split(":")[2];
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) {
      await sendMessage(chatId, "Привычка не найдена.", articlesMenuKeyboard(userId));
      return;
    }
    await sendMessage(chatId, `${habit.emoji} **${habit.name}** — выбери тему:`, articleTopicsKeyboard(habitId));
    return;
  }

  if (data.startsWith("article:") && data.split(":").length === 3) {
    const [, habitId, section] = data.split(":");
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) {
      await sendMessage(chatId, "Привычка не найдена.", articlesMenuKeyboard(userId));
      return;
    }
    const text = articleText(habit, section, state.users[userId].timezoneOffset);
    await sendMessage(chatId, text, articleTopicsKeyboard(habitId));
    return;
  }

  if (data.startsWith("relapse:") && !data.startsWith("relapse:confirm:")) {
    const habitId = data.split(":")[1];
    const habit = getHabit(userId, habitId);
    await answerCallback(callback.id);
    if (!habit) return;
    await sendMessage(
      chatId,
      `${habit.emoji} **${habit.name}**\n\nСорвался? Счётчик обнулится, новый цикл начнётся **сегодня**.\n\nЭто не провал — это честный перезапуск.`,
      relapseConfirmKeyboard(habitId)
    );
    return;
  }

  if (data.startsWith("relapse:confirm:")) {
    const habitId = data.split(":")[2];
    const habit = getHabit(userId, habitId);
    if (!habit) {
      await answerCallback(callback.id);
      return;
    }
    const prevDays = habitStats(habit, state.users[userId].timezoneOffset).days;
    logRelapse(userId, habitId);
    await answerCallback(callback.id, "Счётчик обнулён");
    const supportCaption = relapseSupportText(userId, habitId, prevDays);
    await sendBannerBuffer(chatId, "relapse", `${supportCaption}\n\n🎭 _${TONES.pickTone("relapse")}_`, mainKeyboard());
    await sendBannerBuffer(chatId, "start", `🔄 **Новый старт:** ${habit.emoji} **${habit.name}**\n\nСегодня — день один.`, mainKeyboard());
    await sendMessage(chatId, "🔍 **Что стало триггером?**", triggerKeyboard(habitId));
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
    await sendMessage(chatId, "💰 **Сколько ₽ в день** тратишь на эту привычку?\n(Запомню один раз. Напиши число или 0)");
    return;
  }

  if (pending.type === "custom_unit_cost") {
    const moneyPerDay = Math.max(0, Number(text.replace(",", ".")) || 0);
    state.users[userId].awaitingInput = {
      type: "custom_why_quit",
      name: pending.name,
      dailyAmount: pending.dailyAmount,
      moneyPerDay
    };
    saveState();
    await sendMessage(chatId, "💬 **Почему ты бросаешь?**\n1–2 предложения — напомню в трудный момент.\n\nИли напиши «пропустить».");
    return;
  }

  if (pending.type === "custom_why_quit") {
    const whyQuit = text.toLowerCase() === "пропустить" ? "" : cleanText(text).slice(0, 200);
    state.users[userId].awaitingInput = {
      type: "letter_to_self",
      flow: "custom",
      name: pending.name,
      dailyAmount: pending.dailyAmount,
      moneyPerDay: pending.moneyPerDay,
      whyQuit
    };
    saveState();
    await sendMessage(chatId, "✉️ **Письмо себе** — напишу в SOS.\n1–3 предложения от **сегодняшнего** тебя **будущему**.\n\nИли «пропустить».");
    return;
  }

  if (pending.type === "letter_to_self") {
    const letterToSelf = text.toLowerCase() === "пропустить" ? "" : cleanText(text).slice(0, 400);
    if (!canAddHabit(userId)) {
      state.users[userId].awaitingInput = null;
      saveState();
      await sendMessage(chatId, proGateText(), mainKeyboard());
      return;
    }
    if (pending.flow === "custom") {
      addHabit(userId, {
        type: "custom",
        name: pending.name,
        emoji: "🎯",
        dailyAmount: pending.dailyAmount,
        moneyPerDay: pending.moneyPerDay,
        unitCost: pending.moneyPerDay,
        unitLabel: "раз",
        costLabel: "₽/день",
        whyQuit: pending.whyQuit,
        letterToSelf
      });
    } else if (pending.flow === "quick") {
      const preset = HABIT_PRESETS[pending.presetType];
      addHabit(userId, {
        ...preset,
        dailyAmount: preset.dailyAmount,
        moneyPerDay: preset.moneyPerDay,
        unitCost: preset.unitCost,
        minutesPerDay: pending.minutesPerDay ?? preset.minutesPerDay,
        startWeightKg: pending.startWeightKg,
        currentWeightKg: pending.currentWeightKg ?? pending.startWeightKg,
        targetWeightKg: pending.targetWeightKg,
        trackMode: preset.trackMode,
        whyQuit: pending.whyQuit,
        letterToSelf
      });
    } else {
      addHabit(userId, {
        ...HABIT_PRESETS[pending.presetType],
        dailyAmount: pending.dailyAmount,
        moneyPerDay: pending.moneyPerDay,
        unitCost: pending.moneyPerDay,
        minutesPerDay: pending.minutesPerDay,
        startWeightKg: pending.startWeightKg,
        currentWeightKg: pending.currentWeightKg,
        targetWeightKg: pending.targetWeightKg,
        trackMode: pending.trackMode,
        whyQuit: pending.whyQuit,
        letterToSelf
      });
    }
    state.users[userId].awaitingInput = null;
    saveState();
    await onHabitAdded(chatId, userId);
    return;
  }

  if (pending.type === "edit_money") {
    const moneyPerDay = Math.max(0, Number(text.replace(",", ".")) || 0);
    const habit = getHabit(userId, pending.habitId);
    if (habit) {
      habit.moneyPerDay = moneyPerDay;
      habit.unitCost = moneyPerDay;
      saveState();
    }
    state.users[userId].awaitingInput = null;
    saveState();
    await sendStatsWithImages(chatId, userId);
    return;
  }

  if (pending.type === "savings_goal_title") {
    const title = cleanText(text).slice(0, 60);
    if (!title) {
      await sendMessage(chatId, "Напиши название цели текстом.");
      return;
    }
    state.users[userId].awaitingInput = { type: "savings_goal_amount", title };
    saveState();
    await sendMessage(chatId, `🎯 **${title}**\n\nНа какую сумму копишь? (₽)`);
    return;
  }

  if (pending.type === "savings_goal_amount") {
    const targetAmount = Math.max(1, Math.round(Number(text.replace(",", ".")) || 0));
    state.users[userId].savingsGoal = {
      title: pending.title,
      targetAmount,
      spentAmount: state.users[userId].savingsGoal?.spentAmount || 0
    };
    state.users[userId].awaitingInput = null;
    saveState();
    await sendMessage(chatId, `✅ Цель: **${pending.title}** — **${targetAmount} ₽**\n\nПрогресс в /stats · потратил — /spent`, mainKeyboard());
    return;
  }

  if (pending.type === "spent_saved_amount") {
    const amount = Math.max(0, Math.round(Number(text.replace(",", ".")) || 0));
    const user = state.users[userId];
    if (user.savingsGoal) {
      user.savingsGoal.spentAmount = (user.savingsGoal.spentAmount || 0) + amount;
    }
    state.users[userId].awaitingInput = null;
    saveState();
    const goalLine = user.savingsGoal ? `\n\n${goalProgress(user, totalSavedMoney(userId))?.line || ""}` : "";
    await sendMessage(chatId, `💸 Записал **${amount} ₽** из сэкономленного.${goalLine}`, mainKeyboard());
    await maybeSendSavingsBanner(chatId, userId);
    return;
  }

  if (pending.type === "quick_weight") {
    const kg = Number(text.replace(",", "."));
    if (!Number.isFinite(kg) || kg < 30 || kg > 300) {
      await sendMessage(chatId, "Напиши вес в кг, например **80**");
      return;
    }
    state.users[userId].awaitingInput = {
      type: "quick_why_quit",
      presetType: pending.presetType,
      startWeightKg: Math.round(kg * 10) / 10,
      currentWeightKg: Math.round(kg * 10) / 10
    };
    saveState();
    await sendMessage(chatId, "💬 **Почему меняешь питание?** (или «пропустить»)");
    return;
  }

  if (pending.type === "quick_why_quit") {
    const whyQuit = text.toLowerCase() === "пропустить" ? "" : cleanText(text).slice(0, 200);
    if (!canAddHabit(userId)) {
      state.users[userId].awaitingInput = null;
      saveState();
      await sendMessage(chatId, proGateText(), mainKeyboard());
      return;
    }
    state.users[userId].awaitingInput = {
      type: "letter_to_self",
      flow: "quick",
      presetType: pending.presetType,
      whyQuit,
      startWeightKg: pending.startWeightKg,
      currentWeightKg: pending.currentWeightKg,
      minutesPerDay: pending.minutesPerDay
    };
    saveState();
    await sendMessage(chatId, "✉️ **Письмо себе** — пришлю в SOS.\n1–3 предложения. Или «пропустить».");
    return;
  }

  if (pending.type === "preset_minutes_per_day") {
    const normalized = text.toLowerCase();
    const parsed = Number(text.replace(",", "."));
    const minutesPerDay = normalized === "ок" || normalized === "ok"
      ? pending.defaultMinutes
      : Math.max(5, Math.round(parsed || pending.defaultMinutes));
    state.users[userId].awaitingInput = {
      type: "preset_why_quit",
      presetType: pending.presetType,
      dailyAmount: 1,
      minutesPerDay,
      trackMode: "time"
    };
    saveState();
    const preset = HABIT_PRESETS[pending.presetType];
    await sendMessage(
      chatId,
      `${preset.emoji} **${preset.name}** · **${minutesPerDay} мин/день**\n\n💬 **Почему хочешь контролировать?**\nНапомню в SOS. Или «пропустить».`
    );
    return;
  }

  if (pending.type === "preset_weight_current") {
    const kg = Number(text.replace(",", "."));
    if (!Number.isFinite(kg) || kg < 30 || kg > 300) {
      await sendMessage(chatId, "Напиши вес в кг (30–300), например **82.5**");
      return;
    }
    state.users[userId].awaitingInput = {
      type: "preset_weight_target",
      presetType: pending.presetType,
      startWeightKg: Math.round(kg * 10) / 10
    };
    saveState();
    await sendMessage(chatId, `🎯 **Цель веса** в кг? (меньше текущего)\nНапиши число или «пропустить».`);
    return;
  }

  if (pending.type === "preset_weight_target") {
    const normalized = text.toLowerCase();
    let targetWeightKg = null;
    if (normalized !== "пропустить" && normalized !== "skip") {
      const kg = Number(text.replace(",", "."));
      if (Number.isFinite(kg) && kg >= 30 && kg < pending.startWeightKg) {
        targetWeightKg = Math.round(kg * 10) / 10;
      }
    }
    state.users[userId].awaitingInput = {
      type: "preset_why_quit",
      presetType: pending.presetType,
      dailyAmount: 0,
      trackMode: "weight",
      startWeightKg: pending.startWeightKg,
      currentWeightKg: pending.startWeightKg,
      targetWeightKg
    };
    saveState();
    const preset = HABIT_PRESETS[pending.presetType];
    const goalLine = targetWeightKg ? ` · цель **${targetWeightKg}** кг` : "";
    await sendMessage(
      chatId,
      `${preset.emoji} **${preset.name}** · **${pending.startWeightKg}** кг${goalLine}\n\n💬 **Почему меняешь питание?** Или «пропустить».`
    );
    return;
  }

  if (pending.type === "preset_daily_amount") {
    const normalized = text.toLowerCase();
    const parsed = Number(text.replace(",", "."));
    const dailyAmount = normalized === "ок" || normalized === "ok"
      ? pending.defaultAmount
      : Math.max(1, parsed || pending.defaultAmount);
    const preset = HABIT_PRESETS[pending.presetType];
    const defaultMoney = suggestMoneyPerDay(preset, dailyAmount);
    state.users[userId].awaitingInput = {
      type: "preset_money_per_day",
      presetType: pending.presetType,
      dailyAmount,
      defaultMoney,
      trackMode: "money"
    };
    saveState();
    await sendMessage(
      chatId,
      `${preset.emoji} **${preset.name}**\n\n💰 **Сколько ₽ в день** ты тратишь на это?\n(Запомню один раз.)\n\nПодсказка: ~**${defaultMoney} ₽/день**\nНапиши число или «ок» для подсказки.`
    );
    return;
  }

  if (pending.type === "preset_money_per_day") {
    const normalized = text.toLowerCase();
    const parsed = Number(text.replace(",", "."));
    const moneyPerDay = normalized === "ок" || normalized === "ok"
      ? pending.defaultMoney
      : Math.max(0, parsed || pending.defaultMoney);
    state.users[userId].awaitingInput = {
      type: "preset_why_quit",
      presetType: pending.presetType,
      dailyAmount: pending.dailyAmount,
      moneyPerDay,
      trackMode: "money"
    };
    saveState();
    const preset = HABIT_PRESETS[pending.presetType];
    await sendMessage(
      chatId,
      `${preset.emoji} **${preset.name}** · **${moneyPerDay} ₽/день**\n\n💬 **Почему ты бросаешь?**\nНапомню в SOS. Или «пропустить».`
    );
    return;
  }

  if (pending.type === "edit_minutes") {
    const minutesPerDay = Math.max(5, Math.round(Number(text.replace(",", ".")) || 0));
    const habit = getHabit(userId, pending.habitId);
    if (habit) {
      habit.minutesPerDay = minutesPerDay;
      habit.trackMode = "time";
      saveState();
    }
    state.users[userId].awaitingInput = null;
    saveState();
    await sendStatsWithImages(chatId, userId);
    return;
  }

  if (pending.type === "edit_weight") {
    const parts = text.replace(",", ".").split(/\s+/).map(Number).filter((n) => Number.isFinite(n));
    const habit = getHabit(userId, pending.habitId);
    if (habit && parts.length >= 1) {
      habit.currentWeightKg = Math.round(parts[0] * 10) / 10;
      if (habit.startWeightKg == null) habit.startWeightKg = habit.currentWeightKg;
      if (parts.length >= 2) habit.targetWeightKg = Math.round(parts[1] * 10) / 10;
      habit.trackMode = "weight";
      saveState();
    }
    state.users[userId].awaitingInput = null;
    saveState();
    await sendStatsWithImages(chatId, userId);
    return;
  }

  if (pending.type === "preset_why_quit") {
    const whyQuit = text.toLowerCase() === "пропустить" ? "" : cleanText(text).slice(0, 200);
    if (!canAddHabit(userId)) {
      state.users[userId].awaitingInput = null;
      saveState();
      await sendMessage(chatId, proGateText(), mainKeyboard());
      return;
    }
    state.users[userId].awaitingInput = {
      type: "letter_to_self",
      flow: "preset",
      presetType: pending.presetType,
      dailyAmount: pending.dailyAmount,
      moneyPerDay: pending.moneyPerDay,
      minutesPerDay: pending.minutesPerDay,
      trackMode: pending.trackMode,
      startWeightKg: pending.startWeightKg,
      currentWeightKg: pending.currentWeightKg,
      targetWeightKg: pending.targetWeightKg,
      whyQuit
    };
    saveState();
    await sendMessage(chatId, "✉️ **Письмо себе** — пришлю в SOS.\n1–3 предложения. Или «пропустить».");
    return;
  }

  state.users[userId].awaitingInput = null;
  saveState();
}

async function beginQuickAddHabit(userId, chatId, type) {
  const preset = HABIT_PRESETS[type];
  if (!preset) {
    await sendMessage(chatId, "Неизвестный тип.", addHabitKeyboard(userId));
    return;
  }
  if (!canAddHabit(userId)) {
    await sendMessage(chatId, proGateText(), mainKeyboard());
    return;
  }
  if (getHabitByType(userId, type)) {
    await sendMessage(chatId, `${preset.emoji} ${preset.name} уже добавлено.`, mainKeyboard());
    return;
  }
  if (type === "junkfood") {
    state.users[userId].awaitingInput = { type: "quick_weight", presetType: type };
    saveState();
    await sendMessage(chatId, `⚡ **${preset.name}**\n\n⚖️ Сколько весишь сейчас? (кг)`);
    return;
  }
  if (type === "masturbation") {
    state.users[userId].awaitingInput = { type: "quick_why_quit", presetType: type, minutesPerDay: 30 };
    saveState();
    await sendMessage(
      chatId,
      `⚡ **${preset.name}**\n\nПо умолчанию **30 мин/день** — изменишь в /edit\n\n💬 **Почему хочешь контролировать?** (или «пропустить»)`
    );
    return;
  }
  state.users[userId].awaitingInput = { type: "quick_why_quit", presetType: type };
  saveState();
  await sendMessage(
    chatId,
    `⚡ **Быстрый старт:** ${preset.emoji} ${preset.name}\n\nПо умолчанию ~${preset.dailyAmount} ${preset.unitLabel}/день · **${preset.moneyPerDay} ₽/день**\n\n💬 **Почему бросаешь?** (или «пропустить»)\n\n_Сумму потом изменишь: /edit_`
  );
}

async function beginAddHabit(userId, chatId, type) {
  if (type === "custom") {
    if (!canAddHabit(userId)) {
      await sendMessage(chatId, proGateText(), mainKeyboard());
      return;
    }
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
  if (!canAddHabit(userId)) {
    await sendMessage(chatId, proGateText(), mainKeyboard());
    return;
  }

  if (type === "masturbation") {
    state.users[userId].awaitingInput = {
      type: "preset_minutes_per_day",
      presetType: type,
      defaultMinutes: preset.minutesPerDay || 30
    };
    saveState();
    await sendMessage(
      chatId,
      `${preset.emoji} **${preset.name}**\n\n⏳ **Сколько минут в день** уходит на это?\n(Не деньги — время. По умолчанию **30** — напиши число или «ок».)`
    );
    return;
  }

  if (type === "junkfood") {
    state.users[userId].awaitingInput = { type: "preset_weight_current", presetType: type };
    saveState();
    await sendMessage(chatId, `${preset.emoji} **${preset.name}**\n\n⚖️ **Сколько весишь сейчас?** (кг)`);
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
  const nowIso = new Date().toISOString();
  const existing = user.habits.find((h) => h.id === id);
  const base = {
    id,
    type: config.type,
    name: config.name,
    emoji: config.emoji || "🎯",
    quitDate: todayKey(user.timezoneOffset),
    quitAt: nowIso,
    dailyAmount: config.dailyAmount ?? HABIT_PRESETS[config.type]?.dailyAmount ?? 1,
    moneyPerDay: config.moneyPerDay ?? config.unitCost ?? HABIT_PRESETS[config.type]?.moneyPerDay ?? 0,
    unitCost: config.unitCost ?? config.moneyPerDay ?? HABIT_PRESETS[config.type]?.unitCost ?? 0,
    unitLabel: config.unitLabel || HABIT_PRESETS[config.type]?.unitLabel || "раз",
    whyQuit: config.whyQuit || "",
    letterToSelf: config.letterToSelf || "",
    relapses: existing?.relapses || [],
    lastMotivationSlot: {},
    lastMilestoneSent: 0,
    bestStreak: 0,
    lastStreakBannerSent: 0
  };
  const habit = METRICS.mergeHabitConfig(base, config);
  const idx = user.habits.findIndex((h) => h.id === id);
  if (idx >= 0) user.habits[idx] = habit;
  else user.habits.push(habit);
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
  const stats = habitStats(habit, state.users[userId].timezoneOffset);
  habit.bestStreak = Math.max(habit.bestStreak || 0, stats.days);
  habit.relapses.push({ at: new Date().toISOString() });
  const nowIso = new Date().toISOString();
  habit.quitDate = todayKey(state.users[userId].timezoneOffset);
  habit.quitAt = nowIso;
  habit.lastMilestoneSent = 0;
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
    await sendMessage(chatId, "Сначала добавь привычку для отслеживания.", addHabitKeyboard());
    return;
  }

  const habit = pickRandom(user.habits);
  const slot = source === "manual" ? currentSlot(user.timezoneOffset) : source;
  const motivation = pickMotivation(habit.type, slot, habit, user.timezoneOffset, user);
  const statsBlock = relapseStatLine(habit, user.timezoneOffset);
  const caption = `${habit.emoji} **${habit.name}**\n\n${motivation}\n\n${statsBlock}`;
  await sendMotivationWithImage(chatId, caption, habit.type, slot, mainKeyboard());
}

async function sendUrgeHelp(chatId, userId) {
  const user = state.users[userId];
  const habit = user.habits.length ? pickRandom(user.habits) : null;
  const motivation = habit
    ? pickMotivation(habit.type, "urge", habit, user.timezoneOffset, user)
    : pickFrom(MOTIVATION.general.urge);
  const replacement = pickReplacement(habit?.type || "general");
  const whyLine = habit?.whyQuit ? `\n\n💬 **Твоя цель:** _${habit.whyQuit}_` : "";
  const letterLine = habit?.letterToSelf ? `\n\n✉️ **Письмо себе:**\n_${habit.letterToSelf}_` : "";
  const dayStory = habit ? `\n\n${EXTRAS.getDayStory(ARTICLES, habit.type, habitStats(habit, user.timezoneOffset).days)}` : "";
  const playlist = pickPlaylist(habit?.type || "general", "urge");
  const tone = TONES.pickTone("sos");

  await sendBannerBuffer(
    chatId,
    "sos",
    `🚨 **Держись 10 минут**\n\n_${tone}_\n\n📻 ${playlist.label}`,
    {
      inline_keyboard: [
        [{ text: playlist.label, url: playlist.url }],
        [{ text: "⏱ Таймер 10 мин", callback_data: "timer:start" }]
      ]
    }
  );

  const caption = [
    "**HALT — проверь себя:**",
    "🍽 **H** — голоден? · 😤 **A** — злой? · 😔 **L** — один? · 😴 **T** — устал?",
    "",
    motivation,
    whyLine,
    letterLine,
    dayStory,
    "",
    "🔄 **Замени привычку на:**",
    replacement
  ].join("\n");

  await sendMessage(chatId, caption, {
    inline_keyboard: [
      [{ text: "⏱ Таймер 10 мин", callback_data: "timer:start" }],
      [{ text: "🔄 Ещё замена", callback_data: "replace:more" }],
      [{ text: "📊 Прогресс", callback_data: "menu:stats" }, { text: "📤 Поделиться", callback_data: habit ? `share:${habit.id}` : "menu:stats" }],
      [{ text: "😔 Сорвался", callback_data: "menu:relapse" }]
    ]
  });
}

async function sendReplacement(chatId, userId) {
  const user = state.users[userId];
  const habit = user.habits.length ? pickRandom(user.habits) : null;
  const replacement = pickReplacement(habit?.type || "general");
  await sendMessage(chatId, `🔄 Попробуй вместо этого:\n\n${replacement}`, {
    inline_keyboard: [[{ text: "🔄 Ещё идея", callback_data: "replace:more" }]]
  });
}

function pickMotivation(habitType, slot, habit, timezoneOffset = 3, user = null) {
  const pool = [
    ...asArray(MOTIVATION[habitType]?.[slot]),
    ...asArray(MOTIVATION.general[slot]),
    ...asArray(MOTIVATION[habitType]?.urge),
    ...asArray(MOTIVATION.general.urge)
  ].filter(Boolean);

  let message;
  if (user?.motivVariant === "b" && pool.length > 1) {
    const half = Math.ceil(pool.length / 2);
    message = pickRandom(pool.slice(half));
  } else if (user?.motivVariant === "a" && pool.length > 1) {
    message = pickRandom(pool.slice(0, Math.ceil(pool.length / 2)));
  } else {
    message = pickRandom(pool.length ? pool : ["💪 Ты держишься. Это главное."]);
  }

  const stats = habitStats(habit, timezoneOffset);

  message = message
    .replaceAll("{days}", String(stats.days))
    .replaceAll("{savedMoney}", String(stats.savedMoney))
    .replaceAll("{savedUnits}", String(stats.savedUnits))
    .replaceAll("{elapsed}", formatElapsed(stats.elapsed))
    .replaceAll("{savingsIdea}", pickSavingsIdea(stats.savedMoney, habit.type));

  const milestone = EXTRAS.checkMilestone(habit, stats, MOTIVATION);
  if (milestone && stats.days !== habit.lastMilestoneSent) {
    message = `${milestone}\n\n${message}`;
  }

  return message;
}

function pickReplacement(habitType) {
  const pool = [
    ...asArray(REPLACEMENTS[habitType]),
    ...asArray(REPLACEMENTS.general)
  ];
  return pickRandom(pool);
}

function habitStatsBlockText(habit, user) {
  const stats = habitStats(habit, user.timezoneOffset);
  const streakCompare = stats.bestStreak > stats.currentStreak
    ? `📈 До рекорда: **${stats.bestStreak - stats.currentStreak}** ${pluralDays(stats.bestStreak - stats.currentStreak)} · рекорд **${stats.bestStreak}**`
    : stats.bestStreak === stats.currentStreak && stats.currentStreak > 0
      ? "🏅 **Новый личный рекорд!**"
      : null;
  const triggers = EXTRAS.triggersSummary(habit);
  const badges = GAMIFICATION.weeklyBadges(habit, stats);
  const metricBlock = METRICS.formatHabitMetricBlock(habit, stats);
  const tier = VISUAL.streakHoldTier(stats.days) + 1;
  const safeDays = Number.isFinite(stats.days) ? stats.days : 0;

  return [
    `${habit.emoji} **${habit.name}** · этап **${tier}/10**`,
    badges.length ? badges.join(" · ") : null,
    habit.whyQuit ? `💬 _${habit.whyQuit}_` : null,
    relapseStatLine(habit, user.timezoneOffset),
    `⏱ **Держишься:** ${formatElapsed(stats.elapsed)}`,
    `🔥 Streak: **${stats.currentStreak}** ${pluralDays(stats.currentStreak)} · лучший **${stats.bestStreak}**`,
    streakCompare,
    !METRICS.isWeightHabit(habit) ? EXTRAS.getDayStory(ARTICLES, habit.type, safeDays) : null,
    metricBlock,
    METRICS.isMoneyHabit(habit) && stats.savedUnits > 0
      ? `📉 Не потреблено: ~**${stats.savedUnits}** ${habit.unitLabel}`
      : null,
    METRICS.isMoneyHabit(habit) ? formatSavingsBlock(habit, stats) : null,
    triggers ? `🔍 Частые триггеры: ${triggers}` : null,
    stats.relapseCount > 0 ? `⚠️ Срывов: ${stats.relapseCount}` : null,
    `🗓 Старт: ${formatDateTime(habit.quitAt || habit.quitDate)}`
  ]
    .filter(Boolean)
    .join("\n");
}

function statsHeaderText(userId) {
  const user = state.users[userId];
  const levelLine = GAMIFICATION.levelLine(user, (h) => habitStats(h, user.timezoneOffset));
  const moodLine = GAMIFICATION.moodStats(user);
  return [levelLine, moodLine].filter(Boolean).join("\n");
}

function statsFooterText(userId) {
  const user = state.users[userId];
  const totalSaved = totalSavedMoney(userId);
  const goal = goalProgress(user, totalSaved);
  const globalLine = state.global?.holdingCount
    ? `🌍 Сегодня держатся **~${state.global.holdingCount}** человек`
    : "";
  return [goal?.line, globalLine].filter(Boolean).join("\n\n");
}

function statsText(userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    return "Пока нет отслеживаемых привычек.\n\nДобавь курение, алкоголь или свою — и я буду считать дни и присылать мотивацию.";
  }
  const blocks = user.habits.map((h) => habitStatsBlockText(h, user));
  const header = statsHeaderText(userId);
  const footer = statsFooterText(userId);
  return [header, "", blocks.join("\n\n"), footer ? `\n\n${footer}` : ""].filter(Boolean).join("\n");
}

async function sendStatsWithImages(chatId, userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    await sendMessage(chatId, statsText(userId), addHabitKeyboard(userId));
    return;
  }
  const header = statsHeaderText(userId);
  if (header) await sendMessage(chatId, `📊 **Прогресс**\n\n${header}`);
  for (const habit of user.habits) {
    const stats = habitStats(habit, user.timezoneOffset);
    const caption = habitStatsBlockText(habit, user);
    const art = VISUAL.readStreakHoldBuffer(Number.isFinite(stats.days) ? stats.days : 0);
    if (art) {
      await sendPhotoFile(chatId, art, caption);
    } else {
      await sendMessage(chatId, caption);
    }
  }
  const footer = statsFooterText(userId);
  if (footer) await sendMessage(chatId, footer, statsKeyboard(userId));
  else await sendMessage(chatId, "—", statsKeyboard(userId));
}

function habitStats(habit, timezoneOffset = 3) {
  ensureHabitTimestamps(habit, timezoneOffset);
  const elapsed = getElapsed(habit);
  const days = elapsed.days;
  const progressDays = elapsed.progressDays;
  const savedUnits = Math.round(progressDays * (habit.dailyAmount || 0));
  const savedMoney = estimateSavedMoney(habit, progressDays);
  const relapseCount = habit.relapses?.length || 0;
  const currentStreak = days;
  const bestStreak = Math.max(currentStreak, habit.bestStreak || 0);

  if (bestStreak > (habit.bestStreak || 0)) {
    habit.bestStreak = bestStreak;
    saveState();
  }

  return { days, hours: elapsed.hours, minutes: elapsed.minutes, progressDays, savedUnits, savedMoney, relapseCount, currentStreak, bestStreak, elapsed };
}

function ensureHabitTimestamps(habit, timezoneOffset = 3) {
  if (!habit.quitAt && habit.quitDate) {
    habit.quitAt = new Date(`${habit.quitDate}T00:00:00.000Z`).toISOString();
  }
  if (!habit.quitDate && habit.quitAt) {
    habit.quitDate = habit.quitAt.slice(0, 10);
  }
  if (!habit.quitAt && !habit.quitDate) {
    const nowIso = new Date().toISOString();
    habit.quitAt = nowIso;
    habit.quitDate = todayKey(timezoneOffset);
    saveState();
  }
}

function getElapsed(habit) {
  const start = new Date(habit.quitAt || habit.quitDate);
  if (Number.isNaN(start.getTime())) {
    const zero = { ms: 0, days: 0, hours: 0, minutes: 0, progressDays: 0, totalHours: 0 };
    return zero;
  }
  const ms = Math.max(0, Date.now() - start.getTime());
  const days = Math.floor(ms / 86400000);
  const hours = Math.floor((ms % 86400000) / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  const progressDays = ms / 86400000;
  return { ms, days, hours, minutes, progressDays, totalHours: ms / 3600000 };
}

function formatElapsed(elapsed) {
  const days = Number.isFinite(elapsed.days) ? elapsed.days : 0;
  const hours = Number.isFinite(elapsed.hours) ? elapsed.hours : 0;
  const minutes = Number.isFinite(elapsed.minutes) ? elapsed.minutes : 0;
  const parts = [];
  if (days > 0) parts.push(`**${days}** ${pluralDays(days)}`);
  parts.push(`**${hours}** ч`);
  parts.push(`**${minutes}** мин`);
  return parts.join(" ");
}

function formatDateTime(value) {
  if (!value) return "—";
  if (String(value).includes("T")) {
    const date = new Date(value);
    const dd = String(date.getUTCDate()).padStart(2, "0");
    const mm = String(date.getUTCMonth() + 1).padStart(2, "0");
    const yyyy = date.getUTCFullYear();
    const hh = String(date.getUTCHours()).padStart(2, "0");
    const min = String(date.getUTCMinutes()).padStart(2, "0");
    return `${dd}.${mm}.${yyyy} ${hh}:${min}`;
  }
  return formatDate(value);
}

function estimateSavedMoney(habit, progressDays) {
  const perDay = getMoneyPerDay(habit);
  if (!perDay) return 0;
  return Math.round(progressDays * perDay);
}

function getMoneyPerDay(habit) {
  if (habit.moneyPerDay != null && habit.moneyPerDay >= 0) return habit.moneyPerDay;
  if (habit.type === "smoking" && habit.unitCost) {
    return Math.round(((habit.dailyAmount || 20) / 20) * habit.unitCost);
  }
  return habit.unitCost || 0;
}

function suggestMoneyPerDay(preset, dailyAmount) {
  if (preset.type === "smoking" && preset.unitCost) {
    return Math.max(0, Math.round((dailyAmount / 20) * preset.unitCost));
  }
  return preset.moneyPerDay ?? preset.unitCost ?? 0;
}

function pickSavingsIdea(amount, habitType) {
  const tiers = SAVINGS_IDEAS?.by_amount || [];
  const tier = tiers.find((t) => amount >= t.min && amount < t.max) || tiers[tiers.length - 1];
  const typeIdeas = asArray(SAVINGS_IDEAS?.by_type?.[habitType] || SAVINGS_IDEAS?.by_type?.custom);
  const ideas = [...asArray(tier?.ideas), ...typeIdeas];
  return pickRandom(ideas.length ? ideas : ["что-то приятное для себя"]);
}

function formatSavingsBlock(habit, stats) {
  if (!METRICS.isMoneyHabit(habit)) return null;
  const perDay = getMoneyPerDay(habit);
  if (!perDay) return null;
  const perHour = Math.max(1, Math.round(perDay / 24));
  const idea = pickSavingsIdea(Math.max(stats.savedMoney, perDay), habit.type);
  return [
    `💰 **Сэкономлено:** ~**${stats.savedMoney} ₽** за ${formatElapsed(stats.elapsed)}`,
    `📊 Было **${perDay} ₽/день** · копится ~**${perHour} ₽/час**`,
    `💡 **На это можно:** ${idea}`
  ].join("\n");
}

function habitsText(userId) {
  const user = state.users[userId];
  if (!user.habits.length) return "Список пуст. Добавь первую привычку 👇";
  return [
    "📋 **Твои привычки:**",
    "",
    ...user.habits.map((habit) => {
      const stats = habitStats(habit, user.timezoneOffset);
      return `${habit.emoji} ${habit.name} — ${stats.days} ${pluralDays(stats.days)} ${stats.hours} ч ${stats.minutes} мин`;
    }),
    "",
    "🗑 Чтобы **удалить** — нажми кнопку с корзиной или **🗑 Удалить** в меню."
  ].join("\n");
}

function deleteHabitIntroText() {
  return "🗑 **Удалить привычку**\n\nВыбери, какую убрать из трекера.\nСтатистика по ней будет удалена без восстановления.";
}

function settingsText(userId) {
  const user = state.users[userId];
  const slots = user.reminders.slots.length
    ? user.reminders.slots.map(slotLabel).join(", ")
    : "выключены";
  const quiet = user.quietHours || { enabled: false, start: 23, end: 8 };
  const freezeMonth = EXTRAS.monthKey(new Date(), user.timezoneOffset);
  const allowance = GAMIFICATION.freezeAllowance(user, EXTRAS.monthKey, user.timezoneOffset);
  const used = (user.freezeUsedMonths || []).filter((m) => m === freezeMonth).length;
  const freezeLeft = `${Math.max(0, allowance - used)}/${allowance} в месяце${user.referralCount ? ` (+${Math.min(2, user.referralCount)} реф.)` : ""}`;
  const vacationLine = GAMIFICATION.isOnVacation(user) ? "🏖 **Режим отдыха** активен" : null;
  return [
    "⚙️ **Настройки**",
    vacationLine,
    `🔔 Напоминания: ${user.reminders.enabled ? "включены" : "выключены"}`,
    `🕐 Слоты: ${slots}`,
    `🌙 Вечерний дайджест: ${user.digestEvening !== false ? "одним сообщением" : "как обычно"}`,
    `🔕 Тихие часы (${quiet.start}:00–${quiet.end}:00): ${quiet.enabled ? "вкл" : "выкл"}`,
    `❄️ Заморозка streak: ${freezeLeft}`,
    `🌍 Часовой пояс: UTC${user.timezoneOffset >= 0 ? "+" : ""}${user.timezoneOffset}`,
    "",
    "Напоминания приходят 1 раз в выбранный слот. Вечером — сводка по всем привычкам."
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
    "• **статьи**: польза, синдромы, как справиться",
    "• сравнение: **лучше X% людей** на твоём этапе",
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
    "/urge — SOS: HALT, таймер, Radio Gram",
    "/edit — ₽/день, минуты или вес",
    "/weight — обновить вес (питание)",
    "/goal — цель «коплю на…»",
    "/spent — потратил сэкономленное",
    "/share — карточка streak (картинка)",
    "/calendar — emoji-календарь 14/30 дней",
    "/luck — мотивация дня (1×/день)",
    "/vacation — тихий режим отдыха 3 дня",
    "/pro — Pro (Stars)",
    "/support — TON + СБП",
    "/freeze — заморозка streak (1×/мес + реф.)",
    "/challenge — челлендж с другом",
    "/buddy — сравнение с другом",
    "/habits — список привычек",
    "/delete — удалить привычку",
    "/relapse — сорвался, обнулить счётчик",
    "/articles — статьи по привычкам",
    "/links — радио, музыка, донат",
    "/settings — напоминания, тихие часы",
    "/help — эта справка",
    "",
    "Кнопка **SOS** — когда накрывает прямо сейчас."
  ].join("\n");
}

function relapseIntroText() {
  return "😔 **Сорвался?**\n\nВыбери привычку — **обнулю счётчик**, новый streak начнётся с **сегодня**.\n\nЭто не конец. Честность с собой — уже сила.";
}

function relapseSupportText(userId, habitId, prevDays = 0) {
  const habit = getHabit(userId, habitId);
  if (!habit) return "Записал. Дыши. Ты можешь начать снова прямо сейчас.";
  return [
    `${habit.emoji} **${habit.name}** — срыв записан.`,
    prevDays > 0 ? `📉 Streak **${prevDays}** ${pluralDays(prevDays)} обнулён. Новый старт: **сегодня**.` : "🔄 Счётчик обнулён. Новый старт: **сегодня**.",
    "",
    pickMotivation(habit.type, "urge", habit, state.users[userId].timezoneOffset, state.users[userId]),
    "",
    "💪 Один срыв не стирает весь путь. Ты уже знаешь, что можешь."
  ].join("\n");
}

function articlesIntroText() {
  return "📚 **Статьи по привычкам**\n\nВыбери привычку — расскажу про:\n• пользу отказа\n• экономию\n• синдромы по дням\n• как справляться с тягой";
}

function articleText(habit, section, timezoneOffset) {
  const type = ARTICLES[habit.type] ? habit.type : "custom";
  const block = ARTICLES[type];
  let text = block[section] || block.benefits;
  if (section === "withdrawal") {
    const stats = habitStats(habit, timezoneOffset);
    text += `\n\n${EXTRAS.getDayStory(ARTICLES, habit.type, stats.days)}`;
  }
  if (section === "savings") {
    const stats = habitStats(habit, timezoneOffset);
    const savings = formatSavingsBlock(habit, stats);
    if (savings) {
      text += `\n\n${savings}`;
    } else {
      text += `\n\n📊 **Твой streak:** **${stats.days}** ${pluralDays(stats.days)} ${stats.hours} ч ${stats.minutes} мин без срыва.`;
      if (stats.savedUnits > 0) {
        text += `\n📉 Не потреблено: ~**${stats.savedUnits}** ${habit.unitLabel}.`;
      }
    }
  }
  return text;
}

function getSurvivalPercent(habitType, progressDays) {
  const table = ARTICLES.survival_percent[habitType] || ARTICLES.survival_percent.custom;
  const keys = Object.keys(table).map(Number).sort((a, b) => a - b);
  if (progressDays <= keys[0]) return table[String(keys[0])];
  if (progressDays >= keys[keys.length - 1]) return table[String(keys[keys.length - 1])];

  for (let i = 0; i < keys.length - 1; i += 1) {
    const left = keys[i];
    const right = keys[i + 1];
    if (progressDays >= left && progressDays <= right) {
      const leftVal = table[String(left)];
      const rightVal = table[String(right)];
      const ratio = (progressDays - left) / (right - left);
      return Math.round(leftVal + (rightVal - leftVal) * ratio);
    }
  }
  return table[String(keys[0])];
}

function getRelapsePercent(habitType, progressDays) {
  return clamp(100 - getSurvivalPercent(habitType, progressDays), 1, 99);
}

function relapseStatLine(habit, timezoneOffset) {
  ensureHabitTimestamps(habit, timezoneOffset);
  const elapsed = getElapsed(habit);
  const type = ARTICLES[habit.type] ? habit.type : "custom";

  if (elapsed.ms < 60000) {
    return "🚀 **Старт** — каждая минута без срыва уже победа.";
  }

  const relapse = getRelapsePercent(type, elapsed.progressDays);
  const survive = 100 - relapse;

  return [
    `⏱ **Без срыва:** ${formatElapsed(elapsed)}`,
    `📉 К этому моменту по статистике срываются **~${relapse}%** людей`,
    `🏅 Ты держишься **лучше ~${survive}%** на этом этапе`
  ].join("\n");
}

function linksIntroText() {
  return [
    "🎧 **Музыка для твоих побед и отдыха**",
    "",
    "Включай **Radio Gram** — когда нужен фон, драйв или просто выдохнуть.",
    "",
    "☕ А если бот помогает — можно угостить «безработного разработчика» 😄"
  ].join("\n");
}

function linksKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "📻 Онлайн радио Radio Gram", url: RADIO_GRAM_URL }],
      [{ text: "🎵 Музыка для побед и отдыха", url: CHANNEL_URL }],
      [{ text: "💎 TON-кошелёк", copy_text: { text: TON_WALLET } }],
      [{ text: "💳 СБП · CloudTips", url: SUPPORT_URL }]
    ]
  };
}

function pickImageName(habitType, slot) {
  const pool = [
    ...asArray(IMAGES_META[habitType]),
    ...asArray(IMAGES_META[slot]),
    ...asArray(IMAGES_META.general)
  ].filter(Boolean);
  return pickRandom(pool.length ? pool : null);
}

function resolveImagePath(fileName) {
  if (!fileName) return null;
  const candidates = [
    path.join(IMAGES_DIR, fileName),
    path.join(ROOT_DIR, "images", fileName),
    path.join(ROOT_DIR, "data", fileName)
  ];
  return candidates.find((filePath) => fs.existsSync(filePath)) || null;
}

async function sendMotivationWithImage(chatId, caption, habitType, slot, replyMarkup) {
  const imageName = pickImageName(habitType, slot);
  const imagePath = resolveImagePath(imageName);
  if (imagePath) return sendPhotoFile(chatId, imagePath, caption, replyMarkup);
  return sendMessage(chatId, caption, replyMarkup);
}

async function sendPhotoFile(chatId, imagePathOrArt, caption, replyMarkup) {
  if (SELF_TEST) return sendMessage(chatId, caption, replyMarkup);

  let buffer;
  let filename;
  if (imagePathOrArt && typeof imagePathOrArt === "object" && imagePathOrArt.buffer) {
    buffer = imagePathOrArt.buffer;
    filename = imagePathOrArt.filename || "banner.png";
  } else {
    buffer = fs.readFileSync(imagePathOrArt);
    filename = path.basename(imagePathOrArt);
  }

  const form = new FormData();
  form.append("chat_id", String(chatId));
  form.append("photo", new Blob([buffer], { type: "image/png" }), filename);
  form.append("caption", caption.slice(0, 1024));
  form.append("parse_mode", "Markdown");
  if (replyMarkup) form.append("reply_markup", JSON.stringify(replyMarkup));

  const response = await fetch(`${telegramApi}/sendPhoto`, { method: "POST", body: form });
  const data = await response.json();
  if (!data.ok) {
    console.error("sendPhoto failed:", data.description);
    return sendMessage(chatId, caption, replyMarkup);
  }
  return data;
}

async function sendBannerBuffer(chatId, kind, caption, replyMarkup) {
  const art = VISUAL.readBannerBuffer(kind);
  if (SELF_TEST || !art) return sendMessage(chatId, caption, replyMarkup);
  return sendPhotoFile(chatId, art, caption, replyMarkup);
}

function canAddHabit(userId) {
  const user = state.users[userId];
  return (user.habits?.length || 0) < GAMIFICATION.freeHabitLimit(user);
}

function proGateText() {
  return "⭐ **Free:** до **3** привычек.\n\n/pro — безлимит, все баннеры и календарь 30 дней.";
}

function pickPlaylist(habitType, slot) {
  const typeCfg = PLAYLISTS[habitType];
  if (typeCfg?.[slot]?.url) return typeCfg[slot];
  if (PLAYLISTS[slot]?.url) return PLAYLISTS[slot];
  if (typeCfg?.url) return typeCfg;
  return PLAYLISTS.general;
}

async function sendSupportMenu(chatId) {
  await sendMessage(
    chatId,
    "☕ **Поддержать A-Moral Track · Radio Gram**\n\nСпасибо, что бот помогает 💚",
    supportKeyboard(SUPPORT_URL, TON_WALLET)
  );
}

async function sendDailyLuck(chatId, userId) {
  const user = state.users[userId];
  const dayKey = todayKey(user.timezoneOffset);
  if (user.lastLuckDay === dayKey) {
    await sendMessage(chatId, "🎲 Уже крутил сегодня. Завтра — новая монетка!", mainKeyboard());
    return;
  }
  user.lastLuckDay = dayKey;
  saveState();
  const pool = [...asArray(MOTIVATION.general?.morning), ...asArray(MOTIVATION.general?.evening)];
  const quote = pickRandom(pool.length ? pool : ["💪 Ты держишься. Это главное."]);
  const cap = `🎲 **Мотивация дня**\n\n${quote}\n\n_${TONES.pickTone("luck")}_`;
  await sendBannerBuffer(chatId, "luck", cap, mainKeyboard());
}

async function onHabitAdded(chatId, userId, isRestart = false) {
  const user = state.users[userId];
  const habit = user.habits[user.habits.length - 1];
  if (!habit) return;
  const whyLine = habit.whyQuit ? `\n💬 _${habit.whyQuit}_` : "";
  const cap = isRestart
    ? `🔄 **Перезапуск** ${habit.emoji} **${habit.name}**\n\nСегодня — день один.${whyLine}`
    : `🚀 **Старт!** ${habit.emoji} **${habit.name}**${whyLine}\n\n_${TONES.pickTone("general")}_`;
  await sendBannerBuffer(chatId, "start", cap, mainKeyboard());
  await sendStatsWithImages(chatId, userId);
  const lvl = GAMIFICATION.checkLevelUp(user, (h) => habitStats(h, user.timezoneOffset));
  saveState();
  if (lvl.up) {
    await sendBannerBuffer(
      chatId,
      "levelup",
      `⭐ **Уровень ${lvl.level}**\n\nЗвание: **${lvl.title}** ${lvl.emoji}`,
      mainKeyboard()
    );
  }
}

async function maybeSendStreakBanner(chatId, habit, stats) {
  if (!EXTRAS.MILESTONE_DAYS.includes(stats.days)) return;
  if (habit.lastStreakBannerSent === stats.days) return;
  habit.lastStreakBannerSent = stats.days;
  saveState();
  await sendBannerBuffer(
    chatId,
    "streak",
    `🔥 **${stats.days}** ${pluralDays(stats.days)} без срыва!\n\n${habit.emoji} **${habit.name}**`,
    mainKeyboard()
  );
  if (stats.currentStreak === stats.bestStreak && stats.bestStreak >= 3) {
    await sendBannerBuffer(
      chatId,
      "record",
      `🏆 **Новый рекорд!**\n\n${habit.emoji} **${habit.name}** — **${stats.bestStreak}** ${pluralDays(stats.bestStreak)}`,
      mainKeyboard()
    );
  }
}

async function maybeSendSavingsBanner(chatId, userId) {
  const user = state.users[userId];
  const totalSaved = totalSavedMoney(userId);
  const goal = goalProgress(user, totalSaved);
  if (!goal?.targetAmount && !user.savingsGoal?.targetAmount) return;
  const prevPct = user.lastSavingsPct || 0;
  const milestone = GAMIFICATION.checkSavingsMilestone(user, goal, prevPct);
  user.lastSavingsPct = goal.pct;
  saveState();
  if (!milestone) return;
  const left = Math.max(0, (user.savingsGoal?.targetAmount || 0) - goal.net);
  const cap = milestone === 100
    ? `🎯 **Цель достигнута!**\n\n**${user.savingsGoal.title}** — 100% 🎉`
    : `💰 **${user.savingsGoal.title}** — **${milestone}%**\n\n${left > 0 ? `Ещё **${left} ₽**` : "Почти там!"}`;
  await sendBannerBuffer(chatId, "savings", cap, mainKeyboard());
}

async function sendWeeklyReport(chatId, userId) {
  await sendMessage(chatId, weeklyReportText(userId), mainKeyboard());
  const user = state.users[userId];
  const top = user.habits.reduce((best, h) => {
    const days = habitStats(h, user.timezoneOffset).days;
    return days > (best?.days || 0) ? { habit: h, days } : best;
  }, null);
  if (!top?.habit) return;
  const stage = GAMIFICATION.getDayStage(top.days);
  await sendBannerBuffer(
    chatId,
    "daystage",
    `📅 **${stage.label}**\n\n${top.habit.emoji} **${top.habit.name}** · день **${top.days}**`,
    mainKeyboard()
  );
}

function mainKeyboard() {
  return {
    keyboard: [
      [{ text: "📊 Прогресс" }, { text: "💬 Мотивация" }],
      [{ text: "🚨 SOS /urge" }, { text: "😔 Сорвался" }],
      [{ text: "📚 Статьи" }, { text: "➕ Добавить" }],
      [{ text: "🎧 Радио & музыка" }, { text: "🗑 Удалить" }],
      [{ text: "📅 Календарь" }, { text: "🎲 Удача" }],
      [{ text: "⚙️ Настройки" }, { text: "☕ Поддержать" }],
      [{ text: "❓ Помощь" }]
    ],
    resize_keyboard: true
  };
}

function statsKeyboard(userId) {
  return {
    inline_keyboard: [
      [{ text: "📤 Поделиться streak", callback_data: "share:menu" }],
      [{ text: "✏️ Изменить параметры", callback_data: "edit:menu" }],
      [{ text: "❄️ Заморозка streak", callback_data: "freeze:use" }],
      [{ text: "💬 Мотивация", callback_data: "menu:motivation" }],
      [{ text: "🚨 SOS", callback_data: "menu:urge" }],
      [{ text: "➕ Добавить привычку", callback_data: "add:menu" }]
    ]
  };
}

function articlesMenuKeyboard(userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    return { inline_keyboard: [[{ text: "➕ Добавить привычку", callback_data: "add:menu" }]] };
  }
  const rows = user.habits.map((habit) => [
    { text: `${habit.emoji} ${habit.name}`, callback_data: `article:pick:${habit.id}` }
  ]);
  rows.push([{ text: "← Главное меню", callback_data: "menu:main" }]);
  return { inline_keyboard: rows };
}

function articleTopicsKeyboard(habitId) {
  return {
    inline_keyboard: [
      [{ text: "🌿 Польза отказа", callback_data: `article:${habitId}:benefits` }],
      [{ text: "💰 Экономия", callback_data: `article:${habitId}:savings` }],
      [{ text: "🧠 Синдромы по дням", callback_data: `article:${habitId}:withdrawal` }],
      [{ text: "🛡 Как справиться", callback_data: `article:${habitId}:cravings` }],
      [{ text: "← К привычкам", callback_data: "article:menu" }]
    ]
  };
}

function relapseConfirmKeyboard(habitId) {
  return {
    inline_keyboard: [
      [{ text: "✅ Да, обнулить счётчик", callback_data: `relapse:confirm:${habitId}` }],
      [{ text: "❌ Нет, держусь!", callback_data: "menu:main" }]
    ]
  };
}

function habitsKeyboard(userId) {
  const user = state.users[userId];
  const rows = user.habits.map((habit) => [
    { text: `🗑 ${habit.emoji} ${habit.name}`, callback_data: `remove:${habit.id}` }
  ]);
  rows.push(
    [{ text: "➕ Добавить", callback_data: "add:menu" }],
    [{ text: "← Главное меню", callback_data: "menu:main" }]
  );
  return { inline_keyboard: rows };
}

function deleteConfirmKeyboard(habitId) {
  return {
    inline_keyboard: [
      [{ text: "✅ Да, удалить", callback_data: `remove:confirm:${habitId}` }],
      [{ text: "❌ Отмена", callback_data: "menu:habits" }]
    ]
  };
}

function addHabitKeyboard(userId) {
  return {
    inline_keyboard: [
      [
        { text: "⚡ Курение", callback_data: "add:quick:smoking" },
        { text: "⚡ Алкоголь", callback_data: "add:quick:alcohol" }
      ],
      [{ text: "🚭 Курение (настроить)", callback_data: "add:smoking" }],
      [{ text: "🍷 Алкоголь (настроить)", callback_data: "add:alcohol" }],
      [{ text: "🧠 Онанизм / порно", callback_data: "add:masturbation" }],
      [{ text: "🍔 Питание / похудение", callback_data: "add:junkfood" }],
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
  const quiet = user.quietHours || { enabled: false };

  return {
    inline_keyboard: [
      [{ text: user.reminders.enabled ? "🔔 Выключить напоминания" : "🔕 Включить напоминания", callback_data: "toggle_reminders" }],
      [{ text: user.digestEvening !== false ? "🌙 Дайджест: вкл" : "🌙 Дайджест: выкл", callback_data: "toggle_digest" }],
      [{ text: quiet.enabled ? "🔕 Тихие часы: вкл" : "🔕 Тихие часы: выкл", callback_data: "toggle_quiet" }],
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
  state.global = state.global || {};
  state.global.holdingCount = EXTRAS.countGlobalHolding(state);
  state.global.updatedAt = new Date().toISOString();
  saveState();

  for (const [userId, user] of Object.entries(state.users)) {
    if (!user.chatId) continue;

    if (user.activeTimer?.endsAt && Date.now() >= user.activeTimer.endsAt) {
      user.activeTimer = null;
      saveState();
      try {
        await sendMessage(
          user.chatId,
          "✅ **10 минут прошло.**\n\nЖелание часто уже слабее. **Как сейчас?**",
          moodKeyboard()
        );
      } catch (error) {
        console.error(`Timer notify failed for ${userId}:`, error.message);
      }
    }

    if (!user.reminders?.enabled || !user.habits.length) continue;

    const hour = currentHour(user.timezoneOffset);
    const quiet = user.quietHours || { enabled: false, start: 23, end: 8 };
    if (EXTRAS.isQuietHour(hour, quiet)) continue;

    const dayKey = todayKey(user.timezoneOffset);
    const isSunday = new Date(Date.now() + user.timezoneOffset * 3600000).getUTCDay() === 0;

    if (isSunday && hour === 11 && user.lastWeeklyDigest !== EXTRAS.weekKey(new Date(), user.timezoneOffset)) {
      user.lastWeeklyDigest = EXTRAS.weekKey(new Date(), user.timezoneOffset);
      saveState();
      try {
        await sendWeeklyReport(user.chatId, userId);
      } catch (error) {
        console.error(`Weekly digest failed for ${userId}:`, error.message);
      }
    }

    for (const slot of user.reminders.slots || DEFAULT_REMINDER_SLOTS) {
      if (hour !== REMINDER_HOURS[slot]) continue;
      if (user.lastReminderDate?.[slot] === dayKey) continue;

      user.lastReminderDate = user.lastReminderDate || {};
      user.lastReminderDate[slot] = dayKey;
      saveState();

      try {
        if (slot === "evening" && user.digestEvening !== false) {
          await sendMessage(user.chatId, eveningDigestText(userId), mainKeyboard());
        } else {
          const habit = pickRandom(user.habits);
          const motivation = pickMotivation(habit.type, slot, habit, user.timezoneOffset, user);
          const playlist = pickPlaylist(habit.type, slot);
          const caption = `🔔 ${slotLabel(slot)}\n\n${habit.emoji} ${habit.name}\n\n${motivation}\n\n${relapseStatLine(habit, user.timezoneOffset)}\n\n📻 ${playlist.label}`;
          await sendMotivationWithImage(user.chatId, caption, habit.type, slot, {
            inline_keyboard: [
              [{ text: playlist.label, url: playlist.url }],
              [{ text: "← Меню", callback_data: "menu:main" }]
            ]
          });
        }

        for (const habit of user.habits) {
          const stats = habitStats(habit, user.timezoneOffset);
          const milestone = EXTRAS.checkMilestone(habit, stats, MOTIVATION);
          if (milestone && habit.lastMilestoneSent !== stats.days) {
            habit.lastMilestoneSent = stats.days;
            saveState();
            await sendMessage(user.chatId, `🎊 **Веха!**\n\n${habit.emoji} ${habit.name}\n\n${milestone}`, mainKeyboard());
            await maybeSendStreakBanner(user.chatId, habit, stats);
          }
        }
        await maybeSendSavingsBanner(user.chatId, userId);
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
      createdAt: new Date().toISOString(),
      lastSeen: new Date().toISOString(),
      quietHours: { enabled: false, start: 23, end: 8 },
      digestEvening: true,
      lastWeeklyDigest: null,
      freezeUsedMonth: null,
      challengeCode: null,
      challengeBuddyId: null,
      savingsGoal: null,
      motivVariant: Math.random() < 0.5 ? "a" : "b",
      activeTimer: null
    };
  }
  const user = state.users[userId];
  if (chatId) user.chatId = chatId;
  user.quietHours = user.quietHours || { enabled: false, start: 23, end: 8 };
  if (user.digestEvening == null) user.digestEvening = true;
  if (!user.motivVariant) user.motivVariant = Math.random() < 0.5 ? "a" : "b";
}

function touchUser(userId, chatId) {
  ensureUser(userId, chatId);
  const user = state.users[userId];
  ADMIN.touchActivity(user);
  if (ADMIN.shouldPersistActivity(user)) {
    ADMIN.markActivitySaved(user);
    saveState();
  }
}

function adminStatsText() {
  const users = state.users || {};
  const withHabits = Object.values(users).filter((u) => (u.habits || []).length > 0).length;
  const withReminders = Object.values(users).filter((u) => u.reminders?.enabled).length;
  const holding = state.global?.holdingCount || 0;
  return ADMIN.buildAdminStats({
    title: "A-Moral Track · admin",
    users,
    extraLines: [
      "",
      `🎯 С привычками: **${withHabits}**`,
      `🔔 Напоминания вкл: **${withReminders}**`,
      `🌍 Держатся сегодня: **~${holding}**`
    ]
  });
}

function getHabit(userId, habitId) {
  return state.users[userId]?.habits.find((habit) => habit.id === habitId);
}

function getHabitByType(userId, type) {
  return state.users[userId]?.habits.find((habit) => habit.type === type);
}

function loadState() {
  if (!fs.existsSync(STATE_PATH)) return { users: {}, global: { holdingCount: 0 } };
  try {
    const parsed = JSON.parse(fs.readFileSync(STATE_PATH, "utf8"));
    return {
      users: parsed.users || parsed,
      global: parsed.global || { holdingCount: 0 }
    };
  } catch {
    return { users: {}, global: { holdingCount: 0 } };
  }
}

function saveState() {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify({ users: state.users, global: state.global || {} }, null, 2));
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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function totalSavedMoney(userId) {
  const user = state.users[userId];
  return (user.habits || []).reduce((sum, habit) => sum + habitStats(habit, user.timezoneOffset).savedMoney, 0);
}

function goalProgress(user, totalSaved) {
  return EXTRAS.goalProgress(user, totalSaved);
}

function shareStreakCard(habit, stats) {
  return EXTRAS.shareStreakCard(habit, stats);
}

function ensureChallengeCode(user) {
  if (!user.challengeCode) {
    user.challengeCode = Math.random().toString(36).slice(2, 8).toUpperCase();
  }
  return user.challengeCode;
}

function linkChallengeBuddy(userId, code) {
  const normalized = String(code || "").toUpperCase();
  if (!normalized) return null;
  ensureUser(userId);
  for (const [otherId, other] of Object.entries(state.users)) {
    if (otherId === userId) continue;
    if (other.challengeCode === normalized) {
      state.users[userId].challengeBuddyId = otherId;
      other.challengeBuddyId = userId;
      saveState();
      return other;
    }
  }
  return null;
}

function buddyText(userId) {
  const user = state.users[userId];
  if (!user.challengeBuddyId) {
    return "👥 Пока нет друга в челлендже.\n\n/challenge — получить код\n/challenge КОД — подключиться";
  }
  const buddy = state.users[user.challengeBuddyId];
  if (!buddy) return "Друг не найден. Попробуй подключиться снова: /challenge";
  return EXTRAS.buddyCompare(user, buddy);
}

async function useStreakFreeze(chatId, userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    await sendMessage(chatId, "Сначала добавь привычку.", addHabitKeyboard(userId));
    return;
  }
  if (!GAMIFICATION.canUseFreeze(user, EXTRAS.monthKey, user.timezoneOffset)) {
    const allowance = GAMIFICATION.freezeAllowance(user, EXTRAS.monthKey, user.timezoneOffset);
    await sendMessage(
      chatId,
      `❄️ Заморозки на этот месяц исчерпаны (**${allowance}**/мес).\n\nПриведи друга: /start ref_${userId.slice(-6)} — бонус +1.`,
      mainKeyboard()
    );
    return;
  }
  const habit = user.habits.reduce((best, h) => {
    const days = habitStats(h, user.timezoneOffset).days;
    return days > (best?.days || 0) ? { habit: h, days } : best;
  }, null)?.habit || user.habits[0];
  const start = new Date(habit.quitAt || habit.quitDate);
  habit.quitAt = new Date(start.getTime() - 86400000).toISOString();
  habit.quitDate = habit.quitAt.slice(0, 10);
  GAMIFICATION.markFreezeUsed(user, EXTRAS.monthKey, user.timezoneOffset);
  saveState();
  const left = GAMIFICATION.freezeAllowance(user, EXTRAS.monthKey, user.timezoneOffset)
    - (user.freezeUsedMonths || []).filter((m) => m === EXTRAS.monthKey(new Date(), user.timezoneOffset)).length;
  await sendMessage(
    chatId,
    `❄️ **Заморозка применена**\n\n${habit.emoji} ${habit.name} — +1 день к streak.\n\nОсталось в месяце: **${left}**.`,
    mainKeyboard()
  );
}

function eveningDigestText(userId) {
  const user = state.users[userId];
  const lines = ["🌙 **Вечерний дайджест**", ""];
  for (const habit of user.habits) {
    const stats = habitStats(habit, user.timezoneOffset);
    lines.push(`${habit.emoji} **${habit.name}** — ${formatElapsed(stats.elapsed)}`);
    if (habit.whyQuit) lines.push(`💬 _${habit.whyQuit}_`);
    lines.push(EXTRAS.getDayStory(ARTICLES, habit.type, stats.days));
    lines.push("");
  }
  const goal = goalProgress(user, totalSavedMoney(userId));
  if (goal) lines.push(goal.line);
  if (state.global?.holdingCount) {
    lines.push(`\n🌍 Сегодня держатся **~${state.global.holdingCount}** человек`);
  }
  return lines.join("\n");
}

function weeklyReportText(userId) {
  const user = state.users[userId];
  const weekAgo = Date.now() - 7 * 86400000;
  const lines = ["📅 **Недельный отчёт**", ""];
  let totalSaved = 0;
  let relapsesWeek = 0;
  for (const habit of user.habits) {
    const stats = habitStats(habit, user.timezoneOffset);
    totalSaved += stats.savedMoney;
    const weekRelapses = (habit.relapses || []).filter((r) => new Date(r.at).getTime() >= weekAgo).length;
    relapsesWeek += weekRelapses;
    const badges = GAMIFICATION.weeklyBadges(habit, stats);
    lines.push(
      `${habit.emoji} **${habit.name}**`,
      badges.length ? badges.join(" · ") : null,
      `· streak **${stats.days}** дн. · рекорд **${stats.bestStreak}**`,
      `· срывов за неделю: **${weekRelapses}**`,
      `· сэкономлено ~**${stats.savedMoney} ₽**`,
      ""
    );
  }
  lines.push(`💰 Всего ~**${totalSaved} ₽** · срывов за неделю: **${relapsesWeek}**`);
  const compare = GAMIFICATION.weekCompare(user, (h) => habitStats(h, user.timezoneOffset), user.timezoneOffset);
  if (compare) lines.push("", compare);
  saveState();
  const wk = EXTRAS.weekKey(new Date(), user.timezoneOffset);
  if (user.lastWhyReminder !== wk) {
    user.lastWhyReminder = wk;
    saveState();
    const whyHabit = user.habits.find((h) => h.whyQuit);
    if (whyHabit) lines.push("", `💬 **Ты обещал:** _${whyHabit.whyQuit}_`);
  }
  const goal = goalProgress(user, totalSaved);
  if (goal) lines.push("", goal.line);
  return lines.filter(Boolean).join("\n");
}

function editHabitKeyboard(userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    return { inline_keyboard: [[{ text: "➕ Добавить", callback_data: "add:menu" }]] };
  }
  return {
    inline_keyboard: user.habits.map((habit) => [
      {
        text: `${habit.emoji} ${habit.name} (${METRICS.isTimeHabit(habit) ? `${METRICS.getMinutesPerDay(habit)} мин` : METRICS.isWeightHabit(habit) ? `${habit.currentWeightKg ?? "—"} кг` : `${getMoneyPerDay(habit)} ₽`})`,
        callback_data: `edit:${habit.id}`
      }
    ])
  };
}

function triggerKeyboard(habitId) {
  return {
    inline_keyboard: [
      [
        { text: "☕ Кофе", callback_data: `trigger:${habitId}:coffee` },
        { text: "😤 Стресс", callback_data: `trigger:${habitId}:stress` }
      ],
      [
        { text: "😔 Один", callback_data: `trigger:${habitId}:alone` },
        { text: "😴 Устал", callback_data: `trigger:${habitId}:tired` }
      ],
      [
        { text: "🎉 Компания", callback_data: `trigger:${habitId}:party` },
        { text: "❓ Другое", callback_data: `trigger:${habitId}:other` }
      ],
      [{ text: "Пропустить", callback_data: "menu:main" }]
    ]
  };
}

async function sendShareMenu(chatId, userId) {
  const user = state.users[userId];
  if (!user.habits.length) {
    await sendMessage(chatId, "Сначала добавь привычку.", addHabitKeyboard(userId));
    return;
  }
  if (user.habits.length === 1) {
    const habit = user.habits[0];
    const stats = habitStats(habit, user.timezoneOffset);
    const cap = `${shareStreakCard(habit, stats)}\n\n_Перешли другу — это победа._`;
    await sendBannerBuffer(chatId, "share", cap, mainKeyboard());
    return;
  }
  await sendMessage(chatId, "📤 Выбери привычку для карточки:", {
    inline_keyboard: user.habits.map((habit) => [
      { text: `${habit.emoji} ${habit.name}`, callback_data: `share:${habit.id}` }
    ])
  });
}

async function runSelfTest() {
  ensureUser("test-merge", 1);
  addHabit("test-merge", {
    ...HABIT_PRESETS.alcohol,
    dailyAmount: 1,
    moneyPerDay: 500,
    unitCost: 500,
    whyQuit: "тест"
  });
  const merged = state.users["test-merge"].habits[0];
  if (!merged.quitAt || !merged.quitDate) {
    throw new Error("mergeHabitConfig must preserve quitAt/quitDate");
  }
  const st = habitStats(merged, 3);
  if (!Number.isFinite(st.days) || st.days > 1) {
    throw new Error(`new habit must start at 0-1 days, got ${st.days}`);
  }
  if (VISUAL.streakHoldTier(st.days) !== 0) {
    throw new Error(`new habit image tier must be 0, got ${VISUAL.streakHoldTier(st.days)}`);
  }

  ensureUser("test", 1);
  addHabit("test", { ...HABIT_PRESETS.smoking, dailyAmount: 15, whyQuit: "Здоровье", letterToSelf: "Ты справишься." });
  const user = state.users.test;
  const habit = user.habits[0];
  user.savingsGoal = { title: "Наушники", targetAmount: 5000, spentAmount: 0 };
  console.log("Level:", GAMIFICATION.getLevel(user, (h) => habitStats(h, 3)));
  console.log("Calendar:\n", GAMIFICATION.calendarText(user, (h) => habitStats(h, 3), 3, 14).slice(0, 120));
  console.log("Tone:", TONES.pickTone("sos"));
  console.log("Banner:", VISUAL.bannerPath("start") ? "OK" : "missing");
  console.log("Stats:\n", statsText("test"));
  console.log("\nEvening digest:\n", eveningDigestText("test").slice(0, 200) + "...");
  console.log("\nWeekly:\n", weeklyReportText("test").slice(0, 200) + "...");
  console.log("\nShare:\n", shareStreakCard(habit, habitStats(habit, 3)));
  console.log("\nSelf-test OK");
}

function assertDeployFiles() {
  const required = [
    "lib/extras.js",
    "lib/admin-stats.js",
    "lib/gamification.js",
    "lib/visual.js",
    "lib/tones.js",
    "lib/bot-helpers.js",
    "lib/habit-metrics.js",
    "config/tones.json",
    "config/playlists.json",
    "assets/alerts/start.png",
    "assets/alerts/sos.png",
    "assets/alerts/hold-01.png",
    "assets/alerts/hold-10.png"
  ];
  const missing = required.filter((rel) => !fs.existsSync(path.join(ROOT_DIR, rel)));
  if (missing.length) {
    console.error("Missing deploy files:\n" + missing.map((f) => `  - ${f}`).join("\n"));
    if (!SELF_TEST) process.exit(1);
  }
}
