/**
 * Banner + support helpers for bot.js
 */
function createBannerSender({ SELF_TEST, telegramApi, sendMessage, sendPhotoFile }) {
  const { readBannerBuffer } = require("./visual");

  async function sendBanner(chatId, kind, caption, replyMarkup = null) {
    const art = readBannerBuffer(kind);
    if (SELF_TEST || !art) {
      await sendMessage(chatId, caption, replyMarkup);
      return;
    }
    await sendPhotoFile(chatId, art.buffer, caption, replyMarkup, art.filename);
  }

  return { sendBanner };
}

function supportKeyboard(SUPPORT_URL, TON_WALLET) {
  return {
    inline_keyboard: [
      [{ text: "💎 TON-кошелёк (скопировать)", copy_text: { text: TON_WALLET } }],
      [{ text: "💳 СБП карта", url: SUPPORT_URL }]
    ]
  };
}

function moodKeyboard() {
  return {
    inline_keyboard: [
      [
        { text: "😌 Легче", callback_data: "mood:ok" },
        { text: "😐 Так себе", callback_data: "mood:meh" },
        { text: "😤 Всё ещё тянет", callback_data: "mood:bad" }
      ]
    ]
  };
}

function proText(user, isPro) {
  if (isPro(user)) {
    return [
      "⭐ **Pro активен**",
      "",
      "• безлимит привычек",
      "• картинки на все вехи",
      "• календарь 30 дней",
      "",
      `До: ${user.proUntil?.slice(0, 10) || "—"}`
    ].join("\n");
  }
  return [
    "⭐ **A-Moral Pro**",
    "",
    "Free: до **3** привычек",
    "Pro: безлимит · все баннеры · календарь 30д",
    "",
    "Оплата Stars — скоро. Пока напиши admin.\n\nРеферал: друг по ссылке `?start=ref_ID` — +1 заморозка/мес (до +2)."
  ].join("\n");
}

module.exports = { createBannerSender, supportKeyboard, moodKeyboard, proText };
