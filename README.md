# Telegram AI Bot

Telegram kanallar uchun aqlli avtomatik javob beruvchi bot. Biznes kanallardagi kommentlarga tez, professional va sotuvga yo'naltirilgan javoblar beradi.

## Xususiyatlari

- 🤖 AI-powered javoblar (OpenAI, Groq, Gemini)
- 📊 Kanal statistikasi va monitoring
- 🛡️ Spam himoyasi va rate limiting
- ⚙️ Admin panel va sozlamalar
- 🔄 Ko'p kanalni qo'llab-quvvatlash
- 📝 Tayyor javob shablonlari

## O'rnatish

### 1. Loyihani klonlash
```bash
git clone <repository-url>
cd telegram-ai-bot
```

### 2. Virtual muhit yaratish
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Konfiguratsiya
```bash
cp .env.example .env
```

`.env` faylini tahrirlang va quyidagi ma'lumotlarni kiriting:
- `BOT_TOKEN` - Telegram bot tokeni
- `OPENAI_API_KEY` - OpenAI API kaliti (ixtiyoriy)
- `GROQ_API_KEY` - Groq API kaliti (ixtiyoriy)
- `GEMINI_API_KEY` - Gemini API kaliti (ixtiyoriy)

### 5. Botni ishga tushirish
```bash
python main.py
```

## Foydalanish

### Bot sozlash
1. Botni Telegram kanalingizga admin qilib qo'shing
2. Kanal uchun discussion group yarating
3. Botga `/start` buyrug'ini yuboring
4. Admin paneldan kanalni ulang

### Admin buyruqlari
- `/start` - Admin menyu
- `/stats` - Statistika
- `/settings` - Sozlamalar

## Loyiha strukturasi

```
telegram-ai-bot/
├── main.py                 # Asosiy fayl
├── requirements.txt        # Python bog'liqliklar
├── .env.example           # Konfiguratsiya namunasi
├── src/
│   ├── bot_handler.py     # Bot boshqaruvchisi
│   ├── config.py          # Konfiguratsiya
│   ├── database.py        # Ma'lumotlar bazasi
│   ├── models/            # Ma'lumot modellari
│   ├── handlers/          # Xabar ishlovchilari
│   └── services/          # Xizmatlar
└── tests/                 # Testlar
```

## Deployment

### VPS da ishga tushirish
1. VPS serverga loyihani yuklang
2. Python 3.8+ o'rnating
3. Yuqoridagi o'rnatish qadamlarini bajaring
4. Systemd service yarating:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/telegram-ai-bot
Environment=PATH=/path/to/telegram-ai-bot/venv/bin
ExecStart=/path/to/telegram-ai-bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

5. Serviceni ishga tushiring:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## Litsenziya

MIT License

## Yordam

Savollar uchun: [your-email@example.com]"# bot" 
# bot
# RootGPT
