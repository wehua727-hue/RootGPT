# Telegram AI Bot - Sozlash Yo'riqnomasi

## ✅ Bot muvaffaqiyatli yaratildi!

Bot hozir ishlayapti va Telegram orqali xabarlarni qabul qilishga tayyor.

## 📋 Keyingi qadamlar

### 1. AI API kalitlarini sozlash

`.env` faylini oching va quyidagi API kalitlardan kamida bittasini qo'shing:

```env
# OpenAI (tavsiya etiladi)
OPENAI_API_KEY=sk-your-openai-api-key-here

# yoki Groq (tez va bepul)
GROQ_API_KEY=gsk_your-groq-api-key-here

# yoki Google Gemini
GEMINI_API_KEY=your-gemini-api-key-here
```

**API kalitlarini qayerdan olish:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Groq**: https://console.groq.com/keys  
- **Gemini**: https://makersuite.google.com/app/apikey

### 2. Admin user ID ni o'rnatish

O'z Telegram user ID ingizni bilish uchun:
1. @userinfobot ga `/start` yuboring
2. Sizning user ID ni ko'rsatadi
3. `.env` fayliga qo'shing:

```env
ADMIN_USER_IDS=123456789
```

### 3. Botni kanalingizga qo'shish

1. **Telegram kanalingizga boring**
2. **Kanal sozlamalarini oching** (3 nuqta > Manage Channel)
3. **Administrators > Add Admin**
4. **@reactionquality_bot** ni qidiring va admin qilib qo'shing
5. **Barcha huquqlarni bering** (Post messages, Edit messages, Delete messages)

### 4. Discussion Group yaratish

1. **Kanal sozlamalarida** "Discussion" bo'limini toping
2. **"Create Group"** tugmasini bosing
3. **Group nomini kiriting** (masalan: "Kanal Muhokamasi")
4. **Botni bu groupga ham admin qilib qo'shing**

### 5. Botni sozlash

1. **Discussion groupda** `/setup` buyrug'ini yuboring
2. **Botga shaxsiy xabarda** `/start` yuboring
3. **Admin paneldan** sozlamalarni o'zgartiring:
   - AI javoblarini yoqing/o'chiring
   - Trigger so'zlarni qo'shing
   - Javob shablonlarini yarating

## 🎯 Bot qanday ishlaydi

1. **Foydalanuvchi** kanalingizga comment yozadi
2. **Bot** comment mazmunini tahlil qiladi
3. **Agar kerakli so'zlar** topilsa, javob beradi
4. **Javob** AI yoki tayyor shablon orqali yaratiladi
5. **Statistika** admin panelda ko'rsatiladi

## ⚙️ Sozlamalar

### Trigger so'zlar (standart):
- `narx`, `necha`, `qancha` - narx haqida
- `manzil`, `qayerda` - joylashuv haqida  
- `telefon`, `aloqa` - bog'lanish haqida
- `buyurtma`, `sotib olish` - xarid haqida

### Xavfsizlik:
- Har foydalanuvchiga 5 daqiqada 1 marta javob
- Kunlik javob limiti (standart: 100)
- Spam himoyasi
- Blacklist tizimi

## 🔧 Muammolarni hal qilish

### Bot javob bermayapti:
1. AI API kaliti to'g'ri kiritilganini tekshiring
2. Bot discussion groupda admin ekanini tekshiring
3. `/start` orqali AI yoqilganini tekshiring

### "Permission denied" xatosi:
1. Botga barcha admin huquqlari berilganini tekshiring
2. Discussion group to'g'ri ulanganini tekshiring

### AI javoblar yomon:
1. Trigger so'zlarni aniqroq qiling
2. Javob shablonlarini yarating
3. Boshqa AI provider sinab ko'ring

## 📞 Yordam

Savollar bo'lsa:
- README.md faylini o'qing
- Bot loglarini tekshiring (`bot.log` fayli)
- GitHub Issues orqali murojaat qiling

## 🚀 Qo'shimcha imkoniyatlar

- **Ko'p kanal** qo'llab-quvvatlash
- **Statistika** va analytics
- **Custom javob shablonlari**
- **Webhook** orqali tez ishlash
- **Docker** orqali deploy qilish

**Bot tayyor! Omad tilaymiz! 🎉**