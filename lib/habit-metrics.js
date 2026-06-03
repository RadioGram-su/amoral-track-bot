const MASTURBATION_EFFECTS = [
  { maxDay: 0, text: "🧠 **Сейчас:** импульс сильный — это норма первых часов. Не ругай себя." },
  { maxDay: 3, text: "⚡ **День 1–3:** меньше «тумана», сон и утро часто легче. Тяга ещё волнами." },
  { maxDay: 7, text: "🌊 **4–7 дней:** вечер и скука — главные триггеры. Держи телефон подальше." },
  { maxDay: 14, text: "💪 **8–14 дней:** фокус растёт, прокрастинация «на 5 минут» слабеет." },
  { maxDay: 30, text: "🌱 **15–30 дней:** стабильнее настроение, меньше стыда после срывов." },
  { maxDay: 90, text: "⭐ **1–3 мес:** привычка реже управляет стрессом и одиночеством." },
  { maxDay: Infinity, text: "👑 **3+ мес:** новые вечерние ритуалы. Осторожность на скуке и стрессе." }
];

function getTrackMode(habit) {
  if (habit.trackMode) return habit.trackMode;
  if (habit.type === "masturbation") return "time";
  if (habit.type === "junkfood") return "weight";
  return "money";
}

function isTimeHabit(habit) {
  return getTrackMode(habit) === "time";
}

function isWeightHabit(habit) {
  return getTrackMode(habit) === "weight";
}

function isMoneyHabit(habit) {
  return getTrackMode(habit) === "money";
}

function getMinutesPerDay(habit) {
  return Math.max(0, habit.minutesPerDay ?? 30);
}

function savedMinutes(habit, progressDays) {
  return Math.round(progressDays * getMinutesPerDay(habit));
}

function formatMinutes(totalMin) {
  if (totalMin < 60) return `**${totalMin}** мин`;
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return m > 0 ? `**${h}** ч **${m}** мин` : `**${h}** ч`;
}

function getMasturbationConsequence(days) {
  const d = Math.max(0, Math.floor(days));
  for (const row of MASTURBATION_EFFECTS) {
    if (d <= row.maxDay) return row.text;
  }
  return MASTURBATION_EFFECTS[MASTURBATION_EFFECTS.length - 1].text;
}

function weightProgress(habit) {
  const start = habit.startWeightKg;
  const current = habit.currentWeightKg ?? start;
  const target = habit.targetWeightKg;
  if (start == null || current == null) return null;
  const lost = Math.max(0, start - current);
  const toGo = target != null && target < start ? Math.max(0, current - target) : null;
  const pct = target != null && start > target
    ? Math.min(100, Math.round(((start - current) / (start - target)) * 100))
    : null;
  return { start, current, target, lost, toGo, pct };
}

function formatHabitMetricBlock(habit, stats) {
  if (isTimeHabit(habit)) {
    const perDay = getMinutesPerDay(habit);
    const totalMin = savedMinutes(habit, stats.progressDays);
    const elapsedNote = stats.elapsed ? ` · ${formatElapsedShort(stats.elapsed)}` : "";
    return [
      `⏳ **Было ~${perDay} мин/день** на привычку`,
      `🕐 **Вернул себе:** ~${formatMinutes(totalMin)}${elapsedNote}`,
      getMasturbationConsequence(stats.days)
    ].join("\n");
  }

  if (isWeightHabit(habit)) {
    const wp = weightProgress(habit);
    if (!wp) return "⚖️ Укажи вес: /weight **кг**";
    const lines = [
      `⚖️ **Вес:** **${wp.current}** кг (старт **${wp.start}** кг)`,
      wp.lost > 0 ? `📉 **Минус:** **${wp.lost.toFixed(1)}** кг с начала цикла` : null,
      wp.target != null ? `🎯 **Цель:** **${wp.target}** кг${wp.toGo != null && wp.toGo > 0 ? ` · осталось **${wp.toGo.toFixed(1)}** кг` : wp.pct != null && wp.pct >= 100 ? " · **цель!** 🎉" : wp.pct != null ? ` · **${wp.pct}%** пути` : ""}` : "🎯 Цель веса: /edit или при добавлении",
      `🔥 Без срыва по питанию: **${stats.days}** ${pluralDaysRu(stats.days)}`
    ];
    return lines.filter(Boolean).join("\n");
  }

  return null;
}

function formatElapsedShort(elapsed) {
  const parts = [];
  if (elapsed.days > 0) parts.push(`${elapsed.days} дн.`);
  if (elapsed.hours > 0) parts.push(`${elapsed.hours} ч`);
  if (elapsed.minutes > 0) parts.push(`${elapsed.minutes} мин`);
  return parts.join(" ") || "0 мин";
}

function pluralDaysRu(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "дней";
  if (mod10 === 1) return "день";
  if (mod10 >= 2 && mod10 <= 4) return "дня";
  return "дней";
}

function mergeHabitConfig(habit, config) {
  const trackMode = config.trackMode || (config.type === "masturbation" ? "time" : config.type === "junkfood" ? "weight" : "money");
  return {
    ...habit,
    ...config,
    trackMode,
    id: config.id ?? habit.id,
    quitAt: config.quitAt ?? habit.quitAt,
    quitDate: config.quitDate ?? habit.quitDate,
    minutesPerDay: trackMode === "time" ? (config.minutesPerDay ?? habit.minutesPerDay ?? 30) : config.minutesPerDay,
    startWeightKg: config.startWeightKg ?? habit.startWeightKg,
    currentWeightKg: config.currentWeightKg ?? config.startWeightKg ?? habit.currentWeightKg,
    targetWeightKg: config.targetWeightKg ?? habit.targetWeightKg
  };
}

module.exports = {
  getTrackMode,
  isTimeHabit,
  isWeightHabit,
  isMoneyHabit,
  getMinutesPerDay,
  savedMinutes,
  getMasturbationConsequence,
  weightProgress,
  formatHabitMetricBlock,
  mergeHabitConfig,
  pluralDaysRu
};
