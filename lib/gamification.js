const LEVEL_TITLES = [
  { min: 1, title: "Новичок", emoji: "🌱" },
  { min: 4, title: "Боец", emoji: "💪" },
  { min: 8, title: "Стойкий", emoji: "🛡" },
  { min: 15, title: "Veteran", emoji: "⭐" },
  { min: 30, title: "Легенда", emoji: "👑" }
];

const SAVINGS_MILESTONES = [25, 50, 75, 100];

function totalStreakDays(habits, habitStatsFn) {
  return (habits || []).reduce((sum, h) => sum + (habitStatsFn(h)?.days || 0), 0);
}

function getLevel(user, habitStatsFn) {
  const days = totalStreakDays(user.habits, habitStatsFn);
  const level = Math.max(1, Math.floor(days / 3) + 1);
  let title = LEVEL_TITLES[0];
  for (const t of LEVEL_TITLES) {
    if (level >= t.min) title = t;
  }
  return { level, days, title: title.title, emoji: title.emoji };
}

function levelLine(user, habitStatsFn) {
  const { level, title, emoji } = getLevel(user, habitStatsFn);
  return `${emoji} **Уровень ${level}** · звание «**${title}**»`;
}

function checkLevelUp(user, habitStatsFn) {
  const cur = getLevel(user, habitStatsFn);
  const prev = user.lastLevel || 1;
  if (cur.level > prev) {
    user.lastLevel = cur.level;
    return { up: true, ...cur };
  }
  user.lastLevel = cur.level;
  return { up: false, ...cur };
}

function weeklyBadges(habit, stats) {
  const badges = [];
  if (stats.days >= 7) badges.push("🏅 7 дней");
  if (stats.relapseCount === 0 && stats.days >= 3) badges.push("✨ без срывов");
  if (stats.currentStreak === stats.bestStreak && stats.bestStreak >= 3) badges.push("🔥 рекорд");
  return badges;
}

function calendarText(user, habitStatsFn, tz = 3, days = 14) {
  const lines = [`📅 **Календарь** (последние ${days} дней)`, ""];
  for (const habit of user.habits || []) {
    const row = [];
    for (let i = days - 1; i >= 0; i -= 1) {
      const d = new Date(Date.now() + tz * 3600000 - i * 86400000);
      const key = d.toISOString().slice(0, 10);
      const relapsed = (habit.relapses || []).some((r) => r.at.slice(0, 10) === key);
      const started = (habit.quitAt || habit.quitDate || "").slice(0, 10) <= key;
      row.push(relapsed ? "❌" : started ? "✅" : "⬜");
    }
    lines.push(`${habit.emoji} **${habit.name}**`);
    lines.push(row.join(""));
    lines.push("");
  }
  return lines.join("\n").trim();
}

function moodStats(user) {
  const moods = user.sosMoods || [];
  if (!moods.length) return null;
  const ok = moods.filter((m) => m.mood === "ok").length;
  const pct = Math.round((ok / moods.length) * 100);
  return `🧘 После SOS держишься в **~${pct}%** случаев (${moods.length} отметок)`;
}

function recordMood(user, mood) {
  user.sosMoods = user.sosMoods || [];
  user.sosMoods.push({ mood, at: new Date().toISOString() });
  if (user.sosMoods.length > 100) user.sosMoods = user.sosMoods.slice(-100);
}

function isOnVacation(user) {
  if (!user.vacationUntil) return false;
  return Date.now() < new Date(user.vacationUntil).getTime();
}

function startVacation(user, days = 3) {
  user.vacationUntil = new Date(Date.now() + days * 86400000).toISOString();
}

function isPro(user) {
  if (!user.proUntil) return false;
  return Date.now() < new Date(user.proUntil).getTime();
}

function freeHabitLimit(user) {
  return isPro(user) ? 99 : 3;
}

function freezeAllowance(user, monthKeyFn, tz) {
  const base = 1;
  const bonus = Math.min(2, user.referralCount || 0);
  return base + bonus;
}

function canUseFreeze(user, monthKeyFn, tz) {
  const mk = monthKeyFn(new Date(), tz);
  const used = (user.freezeUsedMonths || []).filter((m) => m === mk).length;
  return used < freezeAllowance(user, monthKeyFn, tz);
}

function markFreezeUsed(user, monthKeyFn, tz) {
  const mk = monthKeyFn(new Date(), tz);
  user.freezeUsedMonths = user.freezeUsedMonths || [];
  user.freezeUsedMonths.push(mk);
  user.freezeUsedMonth = mk;
}

function weekCompare(user, habitStatsFn, tz) {
  const weekAgo = Date.now() - 7 * 86400000;
  let relapsesWeek = 0;
  let savedWeek = 0;
  for (const h of user.habits || []) {
    relapsesWeek += (h.relapses || []).filter((r) => new Date(r.at).getTime() >= weekAgo).length;
    savedWeek += habitStatsFn(h)?.savedMoney || 0;
  }
  const prev = user.lastWeekSnapshot || { relapses: 0, saved: 0 };
  const relapseDiff = prev.relapses - relapsesWeek;
  const savedDiff = savedWeek - prev.saved;
  user.lastWeekSnapshot = { relapses: relapsesWeek, saved: savedWeek, at: new Date().toISOString() };
  const parts = [];
  if (relapseDiff > 0) parts.push(`📉 Срывов на **${relapseDiff}** меньше, чем прошлая неделя`);
  if (relapseDiff < 0) parts.push(`⚠️ Срывов на **${Math.abs(relapseDiff)}** больше — бывает`);
  if (savedDiff > 0) parts.push(`💰 +**${savedDiff} ₽** к сэкономленному vs прошлая неделя`);
  return parts.length ? parts.join("\n") : null;
}

function checkSavingsMilestone(user, goal, prevPct) {
  if (!goal?.targetAmount) return null;
  const pct = goal.pct;
  for (const m of SAVINGS_MILESTONES) {
    if (pct >= m && (prevPct || 0) < m && !user.savingsMilestonesSent?.includes(m)) {
      user.savingsMilestonesSent = user.savingsMilestonesSent || [];
      user.savingsMilestonesSent.push(m);
      return m;
    }
  }
  return null;
}

function getDayStage(day) {
  if (day <= 3) return { id: "d1", label: "День 1–3" };
  if (day <= 7) return { id: "d2", label: "День 4–7" };
  if (day <= 14) return { id: "d3", label: "День 8–14" };
  if (day <= 30) return { id: "d4", label: "День 15–30" };
  return { id: "d5", label: "1+ мес" };
}

module.exports = {
  getLevel,
  levelLine,
  checkLevelUp,
  weeklyBadges,
  calendarText,
  moodStats,
  recordMood,
  isOnVacation,
  startVacation,
  isPro,
  freeHabitLimit,
  canUseFreeze,
  markFreezeUsed,
  freezeAllowance,
  weekCompare,
  checkSavingsMilestone,
  getDayStage,
  SAVINGS_MILESTONES
};
