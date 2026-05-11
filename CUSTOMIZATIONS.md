# CUSTOMIZATIONS

Реестр кастомизаций форка `dfpopov/hll_rcon` поверх апстрима
[`MarechJ/hll_rcon_tool`](https://github.com/MarechJ/hll_rcon_tool).

> Назначение файла: при следующем `git merge upstream/master` сразу видно, какие
> файлы наши и где ждать конфликтов. Обновляйте этот документ при добавлении
> новой кастомизации.

## Как обновляться от апстрима

### Автоматическое обновление на сервере (production)

VPS `95.111.230.75:/root/hll_rcon_tool` обновляется по cron’у:

| Время | Скрипт | Что делает |
|---|---|---|
| `05 03 * * *` | `/root/rcon_update_check.sh` | Проверяет последний релиз `MarechJ/hll_rcon_tool` через GitHub API. Если версия новая — Discord-уведомление «Доступна нова версія CRCON». Версия пишется в `.current_crcon_version`. |
| `00 04 * * *` | `/root/update_crcon.sh` | `git fetch upstream && git merge upstream/master --no-edit`. При успехе: `docker compose build && up -d`, **`git push origin master`**, Discord-уведомление «CRCON оновлено». При конфликте: `git merge --abort` + Discord-уведомление с перечислением конфликтных файлов. |
| `30 04 * * 0` | `docker image prune` + `docker builder prune` | Чистка образов и build cache старше 7 дней. |

Логи: `/var/log/update_crcon.log`, `/var/log/rcon_update_check.log`.

`git push origin master` встроен в `update_crcon.sh` после успешного `docker
compose up -d` — благодаря этому `dfpopov/hll_rcon` всегда содержит актуальную
историю с сервера, и локальный `git pull origin master` забирает свежие мерджи.
Если push падает — отдельный Discord warning «CRCON: push до origin не вдався»
(не фатально для апдейта).

### Ручное обновление на dev-машине

```bash
git fetch upstream
git merge upstream/master            # возможны конфликты в файлах «Зон риска»
# разрешить конфликты, прогнать стек локально
git push origin master
```

### Действия при автоматическом конфликте merge

1. Прочитать Discord-уведомление «CRCON: конфлікт при оновленні» — там
   перечислены конфликтные файлы.
2. SSH на сервер, ручной merge:
   ```bash
   ssh root@95.111.230.75
   cd /root/hll_rcon_tool
   git merge upstream/master
   # разрешить конфликты в редакторе
   git add . && git commit
   docker compose build && docker compose up -d
   git push origin master
   ```
3. Сравнить рабочее поведение CRCON до/после в Discord-канале сервера.

### Бэкапы

Каталог `/root/hll_rcon_tool` периодически копируется в
`/root/hll_rcon_tool_backup_<DATE>/` + tar.gz архив (см. `ls /root/`). Это
страховка на случай сбоя миграции или поломки `db_data/`. Делается вручную
перед существенными апдейтами.

## Реестр кастомизаций

Команда для самопроверки актуальности списка:

```bash
git fetch upstream
git diff --name-status upstream/master..HEAD
git log --no-merges --oneline upstream/master..HEAD
```

### Полностью новые файлы (апстрим их не трогает — конфликтов не будет)

#### Discord-бот (отдельный сервис в docker-стеке)

| Файл | Назначение |
|---|---|
| `bot.py` | Discord-бот, периодически дергает `/api/get_public_info` и обновляет статус сервера в Discord |
| `Dockerfile-bot` | Образ для `bot.py`, собирается в общем стеке |

Конфигурируется через env: `TOKEN`, `BOT_NAME`, `RCON_API_URL`.

#### `custom_tools/` — внешние плагины ElGuillermo

| Файл | Источник | Назначение |
|---|---|---|
| `custom_tools/all_time_stats.py` | [ElGuillermo](https://github.com/ElGuillermo) | Чат-команда и автосообщение при коннекте: показывает all-time статистику игрока |
| `custom_tools/live_topstats.py` | [ElGuillermo](https://github.com/ElGuillermo) | Топ игроков по score с наградами, постит в Discord |
| `custom_tools/common_translations.py` | свой | Общие переводы для двух плагинов выше |

Эти модули импортируют ядро CRCON (`rcon.models`, `rcon.rcon`, `rcon.user_config.*`).
**При апгрейде апстрима их API может поломаться** — проверяйте импорты.

#### Эксплуатация / релизы

| Файл | Назначение |
|---|---|
| `restart.sh` | Полный рестарт стека на VPS |
| `publish-docker.sh` | Сборка и публикация Docker-образов в свой registry |
| `DOCKER_PUBLISH.md` | Документация процесса публикации |

#### Украинская локаль публичного UI

Целиком наши файлы (апстрим украинский не поддерживает):

- `rcongui_public/src/i18n/locales/uk/game.json`
- `rcongui_public/src/i18n/locales/uk/translation.json`
- `rcongui_public/src/i18n/locales/uk/navigation.json`
- `rcongui_public/src/i18n/locales/uk/notfound.json`

### Модифицированные файлы апстрима (потенциальные конфликты при merge)

#### Зоны риска — ядро CRCON

| Файл | +строк | Что менялось |
|---|---|---|
| `rcon/hooks.py` | +370 | Хуки для бота / топстатса (коннект игрока, события матча) |
| `rcon/routines.py` | +281 | Фоновые задачи под кастомные плагины |
| `rcon/settings.py` | +58 | Добавлены настройки для кастомных модулей |
| `rcon/api_commands.py` | +38 | Новые публичные API-методы |
| `rcon/vote_map.py` | +29 | Точечные правки логики голосования за карту |
| `rconweb/rconweb/settings.py` | +8 | Django-настройки (CORS / installed apps) |

> **При апгрейде апстрима внимательно ревьюйте merge именно этих файлов.**
> MarechJ активно меняет `hooks.py` и `routines.py` — здесь конфликты ожидаемы.

#### Инфраструктура и docker

| Файл | Что менялось |
|---|---|
| `compose.yaml` | +150 строк — добавлены сервисы `bot`, `live_topstats`, `all_time_stats` |
| `docker-compose-common-components.yaml` | +30 — общие компоненты под наши сервисы |
| `docker-templates/one-server.yaml` | +2 |
| `docker-templates/ten-servers.yaml` | +2 |
| `config/redis.conf` | +4 — лимиты памяти |
| `default.env` | +6 — переменные для бота и плагинов |

#### CI/CD

| Файл | Что менялось |
|---|---|
| `.github/workflows/docker-images.yml` | Переключено на собственный Docker registry |
| `.github/workflows/docker-images-manual.yml` | Аналогично |
| `.github/workflows/build-docker-images-manual-tag-only.yml` | Аналогично |

#### Локализация (русская)

| Файл | Что менялось |
|---|---|
| `rcongui_public/src/i18n/config.ts` | Регистрация локали `uk` |
| `rcongui_public/src/i18n/locale-provider.tsx` | Подключение `uk` в провайдере |
| `rcongui_public/src/i18n/locales/ru/game.json` | +174 — доперевод |
| `rcongui_public/src/i18n/locales/ru/translation.json` | +32 |
| `rcongui_public/src/i18n/locales/ru/navigation.json` | +8 |
| `rcongui_public/src/i18n/locales/ru/notfound.json` | +6 |

#### Прочее

- `.gitignore`, `README.md` — мелкие правки

## Кастомные коммиты (на момент создания файла, HEAD = `fb5e4867`)

Не-merge коммиты (`git log --no-merges upstream/master..HEAD`):

```
5718dd0d  ops: cap webhook_service at 1G memory and Redis at 2G
35144291  New changes
b0d57927  fix bot
1ae31443  Update compose
8af9e532  Fix bot1
e48193f4  Update bog
ffbb2703  Update bot
0f668cba  Add temporary changes
```

Все авторы — `Dmytro Popov <dmytro.f.popov@gmail.com>`. Остальные коммиты в
`upstream/master..HEAD` — merge-коммиты, тянущие апстрим, не несут собственного
кода.

## Рекомендации по новым кастомизациям

1. Делать в отдельной ветке (`feature/<name>`), а не прямо в `master` — упрощает
   будущие апстрим-мерджи.
2. Осмысленные subject в коммитах: `feat(bot): add server population alert`
   вместо `Update bot`.
3. Новый функционал — по возможности класть **новыми файлами** в `custom_tools/`
   или `bot.py`-стиле, а не править `rcon/hooks.py`. Так проще обновляться.
4. После любого изменения кастома обновить этот файл.
