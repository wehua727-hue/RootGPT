# Requirements Document

## Introduction

Telegram AI Bot loyihasi - bu biznes kanallardagi kommentlarga avtomatik, aqlli va sotuvga yo'naltirilgan javob beradigan bot tizimi. Bot spam bo'lmasligi, foydali va monetizatsiya qilinadigan bo'lishi kerak.

## Glossary

- **Bot**: Telegram Bot API orqali ishlaydigan avtomatik javob beruvchi tizim
- **Channel**: Telegram kanali (biznes kanali)
- **Discussion_Group**: Kanalga ulangan komment guruhi
- **Admin**: Bot va kanal sozlamalarini boshqaruvchi foydalanuvchi
- **AI_Service**: OpenAI/Groq/Gemini kabi AI xizmatlari
- **Comment**: Discussion group dagi foydalanuvchi xabarlari
- **Response**: Bot tomonidan yuborilgan javob
- **Trigger_Word**: Javob berishni faollashtiruvchi kalit so'zlar
- **Database**: SQLite yoki PostgreSQL ma'lumotlar bazasi

## Requirements

### Requirement 1: Bot Channel Integration

**User Story:** Admin sifatida, men botni kanalga admin qilib qo'shishim kerak, shunda bot kanal faoliyatini kuzata olsin.

#### Acceptance Criteria

1. WHEN admin bot tokenini kiritadi, THE Bot SHALL Telegram Bot API orqali ulanishni tasdiqlash
2. WHEN admin kanalga bot qo'shishni so'raydi, THE Bot SHALL kanal admin huquqlarini tekshirish
3. WHEN bot kanalga admin qilib qo'shiladi, THE Bot SHALL kanal ma'lumotlarini Database ga saqlash
4. WHEN kanal discussion group mavjud bo'lsa, THE Bot SHALL discussion group ID sini aniqlash va saqlash

### Requirement 2: Comment Monitoring

**User Story:** Bot sifatida, men discussion group dagi barcha yangi kommentlarni real vaqtda kuzatishim kerak.

#### Acceptance Criteria

1. WHEN yangi komment discussion group ga yoziladi, THE Bot SHALL kommentni darhol qabul qilish
2. WHEN komment qabul qilinadi, THE Bot SHALL komment mazmuni, muallif ma'lumotlari va vaqtini Database ga saqlash
3. WHILE bot faol holatda, THE Bot SHALL barcha ulangan kanallarning discussion group larini kuzatish
4. WHEN komment spam yoki keraksiz bo'lsa, THE Bot SHALL uni e'tiborsiz qoldirish

### Requirement 3: Comment Analysis and Response Generation

**User Story:** Bot sifatida, men komment mazmunini tahlil qilib, mos javob berishim kerak.

#### Acceptance Criteria

1. WHEN komment qabul qilinadi, THE Bot SHALL komment mazmunini kategoriyalash (narx, manzil, aloqa, buyurtma, umumiy savol)
2. WHEN komment kategoriyasi aniqlanadi, THE Bot SHALL mos tayyor javob mavjudligini tekshirish
3. WHERE tayyor javob mavjud bo'lsa, THE Bot SHALL tayyor javobni yuborish
4. WHERE tayyor javob mavjud bo'lmasa va AI javob yoqilgan bo'lsa, THE Bot SHALL AI_Service orqali javob generatsiya qilish
5. WHEN AI javob generatsiya qilinadi, THE Bot SHALL o'zbek tilida, qisqa va professional javob yaratish

### Requirement 4: Response Delivery

**User Story:** Bot sifatida, men yaratilgan javobni to'g'ri formatda va vaqtida yetkazishim kerak.

#### Acceptance Criteria

1. WHEN javob tayyor bo'ladi, THE Bot SHALL javobni discussion group ga reply sifatida yuborish
2. WHEN javob yuboriladi, THE Bot SHALL javob ma'lumotlarini Database ga saqlash
3. IF foydalanuvchi batafsil ma'lumot kerak bo'lsa, THE Bot SHALL foydalanuvchini DM ga yo'naltirish
4. WHEN javob yuboriladi, THE Bot SHALL spam ko'rinishida bo'lmasligini ta'minlash

### Requirement 5: Admin Panel Management

**User Story:** Admin sifatida, men bot sozlamalarini boshqarish uchun qulay interfeys kerak.

#### Acceptance Criteria

1. WHEN admin /start buyrug'ini yuboradi, THE Bot SHALL admin menyusini ko'rsatish
2. WHEN admin kanal ulashni tanlaydi, THE Bot SHALL kanal ulash jarayonini boshlash
3. WHEN admin tayyor javoblar bo'limini ochadi, THE Bot SHALL mavjud javoblarni ko'rsatish va tahrirlash imkonini berish
4. WHEN admin AI javob sozlamalarini ochadi, THE Bot SHALL AI ON/OFF va prompt sozlamalarini taqdim etish
5. WHEN admin trigger so'zlarni sozlaydi, THE Bot SHALL yangi trigger so'zlarni saqlash va eskisini yangilash

### Requirement 6: Security and Anti-Spam

**User Story:** Bot sifatida, men spam va suiiste'mollikni oldini olishim kerak.

#### Acceptance Criteria

1. WHEN bir foydalanuvchi ketma-ket komment yozadi, THE Bot SHALL faqat birinchi kommentga javob berish
2. WHEN flood aniqlansa, THE Bot SHALL vaqtinchalik javob berishni to'xtatish
3. WHERE blacklist mavjud bo'lsa, THE Bot SHALL blacklist dagi foydalanuvchilarga javob bermaslik
4. WHEN kunlik limit tugasa, THE Bot SHALL yangi javob berishni to'xtatish
5. WHILE ishlayotganda, THE Bot SHALL Telegram qoidalariga rioya qilish

### Requirement 7: Statistics and Monitoring

**User Story:** Admin sifatida, men bot faoliyati haqida statistika ko'rishim kerak.

#### Acceptance Criteria

1. WHEN admin statistika bo'limini ochadi, THE Bot SHALL kunlik, haftalik va oylik javoblar sonini ko'rsatish
2. WHEN statistika so'raladi, THE Bot SHALL eng ko'p javob berilgan kategoriyalarni ko'rsatish
3. WHEN monitoring kerak bo'lsa, THE Bot SHALL bot holatini va xatolarni kuzatish
4. WHEN xato yuz bersa, THE Bot SHALL xato ma'lumotlarini log ga yozish

### Requirement 8: AI Integration

**User Story:** Bot sifatida, men AI xizmatlar orqali sifatli javoblar generatsiya qilishim kerak.

#### Acceptance Criteria

1. WHEN AI javob kerak bo'ladi, THE Bot SHALL tanlangan AI_Service ga so'rov yuborish
2. WHEN AI so'rov yuboriladi, THE Bot SHALL o'zbek tilidagi prompt bilan ishlash
3. WHEN AI javob qaytaradi, THE Bot SHALL javobni tekshirish va filtrlash
4. IF AI xizmati ishlamasa, THE Bot SHALL standart javob berish yoki xatoni qayd qilish
5. WHEN AI javob generatsiya qilinadi, THE Bot SHALL javob uzunligi va sifatini nazorat qilish

### Requirement 9: Database Management

**User Story:** Tizim sifatida, men barcha ma'lumotlarni xavfsiz va samarali saqlashim kerak.

#### Acceptance Criteria

1. WHEN bot ishga tushadi, THE Database SHALL zarur jadvallarni yaratish yoki tekshirish
2. WHEN ma'lumot saqlanadi, THE Database SHALL ma'lumot yaxlitligini ta'minlash
3. WHEN ma'lumot o'qiladi, THE Database SHALL tez va samarali qidiruvni ta'minlash
4. WHEN eski ma'lumotlar to'planadi, THE Database SHALL avtomatik tozalash mexanizmini ishlatish
5. WHILE ishlayotganda, THE Database SHALL backup va recovery imkoniyatlarini ta'minlash

### Requirement 10: Configuration Management

**User Story:** Admin sifatida, men bot sozlamalarini oson o'zgartirishim kerak.

#### Acceptance Criteria

1. WHEN bot ishga tushadi, THE Bot SHALL .env fayldan konfiguratsiyani o'qish
2. WHEN sozlamalar o'zgartiriladi, THE Bot SHALL yangi sozlamalarni darhol qo'llash
3. WHEN xavfsiz ma'lumotlar kerak bo'lsa, THE Bot SHALL tokenlar va kalitlarni muhofaza qilish
4. WHERE kanal bo'yicha alohida sozlamalar kerak bo'lsa, THE Bot SHALL har kanal uchun individual sozlamalarni saqlash
5. WHEN bir nechta kanal ulansa, THE Bot SHALL barcha kanallarni parallel ravishda boshqarish