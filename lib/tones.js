const fs = require("fs");
const path = require("path");

const CONFIG_DIR = process.env.BOT_CONFIG_DIR || path.join(__dirname, "..", "config");
const TONES_PATH = path.join(CONFIG_DIR, "tones.json");

const DEFAULT = {
  sos: [
    "Снова «одна не считается»? Считается 😏",
    "Сигарета не решит проблему. Но ты уже знаешь.",
    "Импульс — не команда. Подожди 10 минут."
  ],
  relapse: [
    "Срыв — не конец. Конец — если бросишь бросать.",
    "Честность с собой уже победа. Снова в игру.",
    "Падать можно. Лежать — нет."
  ],
  general: [
    "Ты сильнее привычки. Она просто громче.",
    "Каждый «нет» — +1 к новому ты."
  ]
};

let cache = null;

function load() {
  if (cache) return cache;
  try {
    if (fs.existsSync(TONES_PATH)) cache = JSON.parse(fs.readFileSync(TONES_PATH, "utf8"));
  } catch {
    cache = DEFAULT;
  }
  if (!cache) cache = DEFAULT;
  return cache;
}

function pickTone(slot = "general") {
  const pool = load()[slot] || load().general || DEFAULT.general;
  return pool[Math.floor(Math.random() * pool.length)];
}

module.exports = { pickTone, load };
