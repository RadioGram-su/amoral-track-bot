const MILESTONE_DAYS = [1, 3, 7, 14, 30, 90, 180, 365];

function isQuietHour(hour, quiet) {
  if (!quiet?.enabled) return false;
  const start = quiet.start ?? 23;
  const end = quiet.end ?? 8;
  if (start > end) return hour >= start || hour < end;
  return hour >= start && hour < end;
}

function monthKey(date = new Date(), tz = 3) {
  const local = new Date(date.getTime() + tz * 3600000);
  return `${local.getUTCFullYear()}-${String(local.getUTCMonth() + 1).padStart(2, "0")}`;
}

function weekKey(date = new Date(), tz = 3) {
  const local = new Date(date.getTime() + tz * 3600000);
  const day = local.getUTCDay();
  const diff = local.getUTCDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), diff));
  return monday.toISOString().slice(0, 10);
}

function getDayStory(articles, habitType, day) {
  const type = articles[habitType] ? habitType : "custom";
  const withdrawal = articles[type]?.withdrawal || "";
  const d = Math.max(0, Math.floor(day));
  if (d <= 3) return "🔥 **День 1–3** — пик импульса. Держись, это временно.";
  if (d <= 7) return "🌊 **День 4–7** — волны короче. Сон может сбиться — норма.";
  if (d <= 14) return "⚡ **День 8–14** — психологическая привычка сильнее физической.";
  if (d <= 30) return "🌱 **День 15–30** — легче, но «одна не считается» — ловушка.";
  if (d <= 90) return "💪 **1–3 мес** — редкие импульсы. Организм уже другой.";
  return "⭐ **3+ мес** — новый образ жизни. Осторожность на стрессе.";
}

function checkMilestone(habit, stats, motivation) {
  const milestones = motivation[habit.type]?.milestones || motivation.general?.milestones || {};
  const day = stats.days;
  if (!MILESTONE_DAYS.includes(day)) return null;
  if (habit.lastMilestoneSent === day) return null;
  const text = milestones[String(day)];
  if (!text) return `🎉 **${day} ${day === 1 ? "день" : "дней"}** без срыва! Ты на вехе.`;
  return text;
}

function goalProgress(user, totalSaved) {
  const g = user.savingsGoal;
  if (!g?.targetAmount) return null;
  const net = Math.max(0, totalSaved - (g.spentAmount || 0));
  const pct = Math.min(100, Math.round((net / g.targetAmount) * 100));
  const bar = "█".repeat(Math.floor(pct / 10)) + "░".repeat(10 - Math.floor(pct / 10));
  return {
    net,
    pct,
    line: `🎯 **${g.title}** — ${net}/${g.targetAmount} ₽\n\`${bar}\` ${pct}%`
  };
}

function shareStreakCard(habit, stats, userName = "Я") {
  return [
    "🏆 **A-Moral Track**",
    "",
    `${habit.emoji} **${habit.name}**`,
    `⏱ ${stats.days} дн. ${stats.hours} ч ${stats.minutes} мин без срыва`,
    stats.bestStreak > stats.days ? `🏅 Лучший streak: ${stats.bestStreak} дн.` : null,
    stats.savedMoney > 0 ? `💰 Сэкономлено ~${stats.savedMoney} ₽` : null,
    "",
    "💚 Держусь. Ты тоже можешь."
  ].filter(Boolean).join("\n");
}

function countGlobalHolding(state) {
  let count = 0;
  for (const user of Object.values(state.users || {})) {
    if ((user.habits || []).some((h) => {
      const start = new Date(h.quitAt || h.quitDate);
      return Date.now() - start.getTime() > 3600000;
    })) count += 1;
  }
  return count;
}

function buddyCompare(user, buddy) {
  if (!buddy?.habits?.length) return "Друг ещё не добавил привычки.";
  const lines = ["👥 **Челлендж с другом**", ""];
  for (const habit of user.habits || []) {
    const match = buddy.habits.find((h) => h.type === habit.type || h.name === habit.name);
    if (!match) continue;
    const myDays = Math.floor((Date.now() - new Date(habit.quitAt).getTime()) / 86400000);
    const budDays = Math.floor((Date.now() - new Date(match.quitAt).getTime()) / 86400000);
    const lead = myDays === budDays ? "🤝 наравне" : myDays > budDays ? "💪 ты впереди" : "🔥 друг впереди";
    lines.push(`${habit.emoji} ${habit.name}: **${myDays}** vs **${budDays}** дн. · ${lead}`);
  }
  return lines.join("\n");
}

function triggerLabel(id) {
  return { coffee: "☕ Кофе", stress: "😤 Стресс", alone: "😔 Один", tired: "😴 Устал", party: "🎉 Компания", other: "❓ Другое" }[id] || id;
}

function triggersSummary(habit) {
  const counts = {};
  for (const r of habit.relapses || []) {
    if (!r.trigger) continue;
    counts[r.trigger] = (counts[r.trigger] || 0) + 1;
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return entries.map(([k, v]) => `${triggerLabel(k)}: ${v}`).join(" · ");
}

module.exports = {
  MILESTONE_DAYS,
  isQuietHour,
  monthKey,
  weekKey,
  getDayStory,
  checkMilestone,
  goalProgress,
  shareStreakCard,
  countGlobalHolding,
  buddyCompare,
  triggerLabel,
  triggersSummary
};
