## Telegram бот для скачивания видео (YouTube/Instagram)

Функции:
- Отправьте ссылку в группу (бот должен быть участником, с правом удаления сообщений) — бот удалит исходное сообщение и отправит видео.
- Отправьте ссылку боту в личные сообщения — бот ответит видео.

Поддерживаются ссылки YouTube и Instagram. Загрузка реализована через `yt-dlp`.

### Запуск через Docker Compose

1) Создайте файл `.env` рядом с `docker-compose.yml` и укажите токен бота:

```
BOT_TOKEN=123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
```

2) Запустите:

```
docker compose up -d --build
```

Видео и временные файлы будут сохраняться в каталоге `./downloads` (примонтирован в контейнер как `/downloads`).

### Права бота в группе
Чтобы бот мог удалить ваше исходное сообщение в группе, дайте боту право на удаление сообщений. Если права нет — бот просто отправит видео, не удаляя исходное сообщение.

### Ограничения Telegram
Если видео слишком большое для загрузки ботом, бот отправит сообщение с исходной ссылкой.

### Локальная разработка (необязательно)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
BOT_TOKEN=... DOWNLOAD_DIR=./downloads python -m src.bot
```

### Публикация в GitHub
Выполните команды:

```
git init
git add .
git commit -m "Initial commit: Telegram video bot"
# Создайте репозиторий на GitHub и замените URL нижe на ваш
git remote add origin https://github.com/<your_user>/<your_repo>.git
git branch -M main
git push -u origin main
```
