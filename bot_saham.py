import math
import telebot
import yfinance as yf
import pandas as pd

# Masukkan Token Bot Telegram dari BotFather
TOKEN = "8897000636:AAF5oC1uT98XOrwNHqVUmMWcKB66IQMpNaI"
bot = telebot.TeleBot(TOKEN)


def ambil_data_saham(ticker_input):
  ticker_jk = (
      ticker_input if ticker_input.endswith(".JK") else f"{ticker_input}.JK"
  )

  try:
    stock = yf.Ticker(ticker_jk)
    info = stock.info

    # 1. Harga Realtime
    price_now = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    prev_close = info.get("previousClose", price_now)
    price_high = info.get("dayHigh") or info.get("regularMarketDayHigh")
    price_low = info.get("dayLow") or info.get("regularMarketDayLow")
    volume = info.get("volume") or info.get("regularMarketVolume", 0)

    df = stock.history(period="1mo").dropna(subset=["Close"])

    if not price_now or not price_high:
      if not df.empty:
        price_now = df["Close"].iloc[-1]
        prev_close = (
            df["Close"].iloc[-2] if len(df) >= 2 else df["Open"].iloc[-1]
        )
        price_high = df["High"].iloc[-1]
        price_low = df["Low"].iloc[-1]
        volume = df["Volume"].iloc[-1]

    if not price_now:
      return f"❌ Data saham **{ticker_input}** tidak ditemukan."

    # 2. Indikator Tren (1 Bulan)
    indikator_tren = "N/A"
    if len(df) >= 20:
      sma5 = df["Close"].rolling(window=5).mean().iloc[-1]
      sma20 = df["Close"].rolling(window=20).mean().iloc[-1]
      if price_now > sma5 and sma5 > sma20:
        indikator_tren = "UPTREND 🟢"
      elif price_now < sma5 and sma5 < sma20:
        indikator_tren = "DOWNTREND 🔴"
      else:
        indikator_tren = "SIDEWAYS / NEUTRAL 🟡"

    # 3. Estimasi Total Avg Asing (VWAP 1 Bulan)
    avg_asing_text = "N/A"
    if not df.empty and len(df) >= 5:
      typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
      vwap = (typical_price * df["Volume"]).sum() / df["Volume"].sum()
      diff_pct = ((price_now - vwap) / vwap) * 100
      posisi = (
          f"(+{diff_pct:.1f}% dr Avg)"
          if diff_pct >= 0
          else f"({diff_pct:.1f}% dr Avg)"
      )
      avg_asing_text = f"Rp {vwap:,.0f} {posisi}"

    # 4. EPS TTM Presisi
    eps_ttm = None
    try:
      incomes = stock.quarterly_income_stmt
      if (
          incomes is not None
          and not incomes.empty
          and "Basic EPS" in incomes.index
      ):
        eps_4q = incomes.loc["Basic EPS"].dropna().head(4)
        if len(eps_4q) == 4:
          eps_ttm = float(eps_4q.sum())
    except Exception:
      pass

    if eps_ttm is None:
      eps_ttm = info.get("trailingEps", None) or info.get(
          "epsCurrentYear", None
      )

    # 5. BVPS & Valuasi Graham
    bvps = info.get("bookValue", None)
    currency = info.get("financialCurrency", "IDR").upper()
    if currency == "USD" and bvps:
      bvps = bvps * 15800

    fair_value_text = "N/A"
    status_valuasi = "-"

    if eps_ttm and bvps and eps_ttm > 0 and bvps > 0:
      fair_value = math.sqrt(22.5 * eps_ttm * bvps)
      mos = ((fair_value - price_now) / fair_value) * 100
      fair_value_text = f"Rp {fair_value:,.0f}"
      if price_now < fair_value:
        status_valuasi = f"UNDERVALUED (Diskon {mos:.1f}%)"
      else:
        status_valuasi = f"OVERVALUED (Premium {abs(mos):.1f}%)"

    # 6. Support & Resistance
    pivot = (price_high + price_low + price_now) / 3.0
    r1 = (2 * pivot) - price_low
    s1 = (2 * pivot) - price_high
    r2 = pivot + (price_high - price_low)
    s2 = pivot - (price_high - price_low)

    change_rp = price_now - prev_close
    change_pct = (change_rp / prev_close) * 100 if prev_close else 0
    trend_icon = "+" if change_rp > 0 else ""

    # Format Pesan Telegram (Markdown)
    pesan = f"""
📊 **ANALISIS SAHAM {ticker_input}**
----------------------------------------
• **Harga Sekarang** : Rp {price_now:,.0f}
• **Perubahan**      : {trend_icon}Rp {change_rp:,.0f} ({trend_icon}{change_pct:.2f}%)
• **Indikator Tren** : {indikator_tren}
• **Total Avg Asing**: {avg_asing_text}
----------------------------------------
• **EPS TTM**        : Rp {eps_ttm:,.2f}
• **BVPS (IDR)**     : Rp {bvps:,.2f}
• **Estimasi Wajar** : {fair_value_text}
• **Status Valuasi** : {status_valuasi}
----------------------------------------
📈 [R2] Rp {r2:,.0f} | [R1] Rp {r1:,.0f}
🎯 [PIVOT] Rp {pivot:,.0f}
📉 [S1] Rp {s1:,.0f} | [S2] Rp {s2:,.0f}
----------------------------------------
High: Rp {price_high:,.0f} | Low: Rp {price_low:,.0f}
Vol: {volume:,.0f} lembar
    """
    return pesan

  except Exception as e:
    return f"⚠️ Terjadi kesalahan saat memproses data: {e}"


# Command /start di Telegram
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Halo! Kirim kode saham yang mau dicek.\nContoh: `BBCA`, `GOTO`, atau"
      " `/saham BUVA`",
      parse_mode="Markdown",
  )


# Handler untuk membaca pesan teks biasa atau perintah /saham
@bot.message_handler(func=lambda message: True)
def handle_message(message):
  text = message.text.strip().upper()
  if text.startswith("/SAHAM"):
    text = text.replace("/SAHAM", "").strip()

  if not text:
    bot.reply_to(message, "Silakan masukkan kode saham yang valid.")
    return

  bot.send_chat_action(message.chat.id, "typing")
  hasil = ambil_data_saham(text)
  bot.reply_to(message, hasil, parse_mode="Markdown")


print("Bot Telegram Saham berjalan...")
bot.infinity_polling()
