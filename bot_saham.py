import telebot
import yfinance as yf
import pandas as pd

# Masukkan Token Bot Telegram kamu di bawah ini
TOKEN = "8897000636:AAF5oC1uT98XOrwNHqVUmMWcKB66IQMpNaI"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    teks = (
        "Selamat datang di Bot Monitor Saham!\n\n"
        "Gunakan format berikut untuk mengecek harga saham:\n"
        "• Kirim kode saham Indonesia (contoh: BBCA, TLKM, BBRI)\n"
        "• Kirim kode saham AS (contoh: AAPL, TSLA)"
    )
    bot.reply_to(message, teks)

@bot.message_handler(func=lambda message: True)
def get_stock_info(message):
    kode = message.text.strip().upper()
    
    # Tambahkan suffix .JK jika pengguna tidak memasukkannya untuk saham Indonesia
    ticker_code = kode if kode.endswith(".JK") or "." in kode else f"{kode}.JK"
    
    bot.send_message(message.chat.id, f"Sedang mengambil data untuk {kode}...")
    
    try:
        stock = yf.Ticker(ticker_code)
        info = stock.info
        
        # Jika saham Indonesia tidak ditemukan, coba cari sebagai kode internasional biasa
        if 'regularMarketPrice' not in info or info['regularMarketPrice'] is None:
            stock = yf.Ticker(kode)
            info = stock.info

        harga = info.get('regularMarketPrice') or info.get('currentPrice')
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')

        if harga is not None:
            perubahan = harga - prev_close if prev_close else 0
            persen = (perubahan / prev_close * 100) if prev_close else 0
            tanda = "+" if perubahan > 0 else ""

            balasan = (
                f"📊 Informasi Saham: {kode}\n\n"
                f"• Harga Terakhir: Rp {harga:,.2f}\n"
                f"• Perubahan: {tanda}{perubahan:,.2f} ({tanda}{persen:.2f}%)\n"
                f"• Penutupan Sebelumnya: Rp {prev_close:,.2f}\n"
            )
            bot.reply_to(message, balasan)
        else:
            bot.reply_to(message, f"❌ Data untuk kode saham {kode} tidak ditemukan.")

    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan saat mengambil data: {str(e)}")

if __name__ == "__main__":
    print("Bot berhasil dijalankan...")
    bot.infinity_polling()
