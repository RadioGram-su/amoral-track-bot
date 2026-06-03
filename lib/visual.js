const fs = require("fs");
const path = require("path");

const ASSETS_DIR = path.join(__dirname, "..", "assets", "alerts");

const BANNERS = {
  start: "start.png",
  streak: "streak.png",
  sos: "sos.png",
  relapse: "relapse.png",
  savings: "savings.png",
  record: "record.png",
  luck: "luck.png",
  levelup: "levelup.png",
  share: "share.png",
  daystage: "daystage.png"
};

/** 10 картинок прогресса по дням streak (hold-01 … hold-10) */
const HOLD_FILES = [
  "hold-01.png",
  "hold-02.png",
  "hold-03.png",
  "hold-04.png",
  "hold-05.png",
  "hold-06.png",
  "hold-07.png",
  "hold-08.png",
  "hold-09.png",
  "hold-10.png"
];

function streakHoldTier(days) {
  if (!Number.isFinite(days)) return 0;
  const d = Math.max(0, Math.floor(days));
  if (d === 0) return 0;
  if (d === 1) return 1;
  if (d <= 3) return 2;
  if (d <= 7) return 3;
  if (d <= 14) return 4;
  if (d <= 21) return 5;
  if (d <= 30) return 6;
  if (d <= 60) return 7;
  if (d <= 90) return 8;
  return 9;
}

function readStreakHoldBuffer(days) {
  const tier = streakHoldTier(days);
  const file = HOLD_FILES[tier];
  const p = path.join(ASSETS_DIR, file);
  if (fs.existsSync(p)) {
    return { buffer: fs.readFileSync(p), filename: file, tier: tier + 1 };
  }
  return readBannerBuffer("streak");
}

function bannerPath(kind) {
  const file = BANNERS[kind];
  if (!file) return null;
  const p = path.join(ASSETS_DIR, file);
  return fs.existsSync(p) ? p : null;
}

function readBannerBuffer(kind) {
  const p = bannerPath(kind);
  if (!p) return null;
  return { buffer: fs.readFileSync(p), filename: path.basename(p) };
}

module.exports = {
  bannerPath,
  readBannerBuffer,
  readStreakHoldBuffer,
  streakHoldTier,
  BANNERS,
  HOLD_FILES
};
