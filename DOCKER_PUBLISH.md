# Публикация Docker образов

## Текущая конфигурация

В проекте используются следующие Docker репозитории:
- **Backend**: `dinnamo1927/hll_rcon_tool`
- **Frontend**: `dinnamo1927/hll_rcon_tool_frontend`

## Где настроен репозиторий

### 1. Файлы конфигурации

- **`default.env`** - переменные окружения:
  ```env
  BACKEND_DOCKER_REPOSITORY=dinnamo1927/hll_rcon_tool
  FRONTEND_DOCKER_REPOSITORY=dinnamo1927/hll_rcon_tool_frontend
  ```

### 2. GitHub Actions workflows

- **`.github/workflows/docker-images.yml`** - автоматическая сборка при push тегов
- **`.github/workflows/docker-images-manual.yml`** - ручная сборка через GitHub UI
- **`.github/workflows/build-docker-images-manual-tag-only.yml`** - сборка с указанием тега

## Как изменить репозиторий

### Шаг 1: Обновить default.env

```bash
# Отредактировать default.env
BACKEND_DOCKER_REPOSITORY=ваш_username/hll_rcon_tool
FRONTEND_DOCKER_REPOSITORY=ваш_username/hll_rcon_tool_frontend
```

### Шаг 2: Обновить GitHub Actions workflows

Заменить `dinnamo1927` на ваш username во всех workflow файлах:
- `.github/workflows/docker-images.yml`
- `.github/workflows/docker-images-manual.yml`
- `.github/workflows/build-docker-images-manual-tag-only.yml`

### Шаг 3: Настроить GitHub Secrets

В настройках репозитория GitHub (Settings → Secrets and variables → Actions) должны быть:
- `DOCKERHUB_USERNAME` - ваш Docker Hub username
- `DOCKERHUB_TOKEN` - ваш Docker Hub access token

## Способы публикации

### Вариант 1: Через GitHub Actions (рекомендуется)

#### Автоматическая сборка при создании тега:

```bash
# Создать тег
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions автоматически соберет и опубликует образы.

#### Ручная сборка через GitHub UI:

1. Перейти в **Actions** → **build-docker-images-manual**
2. Нажать **Run workflow**
3. Указать тег (например, `v1.0.0`)
4. Нажать **Run workflow**

### Вариант 2: Локальная сборка и публикация

#### Использовать скрипт:

```bash
# Сделать скрипт исполняемым
chmod +x publish-docker.sh

# Опубликовать с тегом
./publish-docker.sh v1.0.0

# Опубликовать latest
./publish-docker.sh latest
```

#### Или вручную:

```bash
# 1. Войти в Docker Hub
docker login

# 2. Собрать и опубликовать backend
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ваш_username/hll_rcon_tool:latest \
  -t ваш_username/hll_rcon_tool:v1.0.0 \
  --push .

# 3. Собрать и опубликовать frontend
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile-frontend \
  -t ваш_username/hll_rcon_tool_frontend:latest \
  -t ваш_username/hll_rcon_tool_frontend:v1.0.0 \
  --push .
```

## Проверка публикации

```bash
# Проверить, что образы опубликованы
docker pull ваш_username/hll_rcon_tool:latest
docker pull ваш_username/hll_rcon_tool_frontend:latest
```

Или проверить на Docker Hub:
- https://hub.docker.com/r/ваш_username/hll_rcon_tool
- https://hub.docker.com/r/ваш_username/hll_rcon_tool_frontend

## Использование опубликованных образов

В `docker-compose.yaml` или `.env` файле:

```env
BACKEND_DOCKER_REPOSITORY=ваш_username/hll_rcon_tool
FRONTEND_DOCKER_REPOSITORY=ваш_username/hll_rcon_tool_frontend
TAGGED_VERSION=latest  # или конкретный тег, например v1.0.0
```

Затем:

```bash
docker compose pull
docker compose up -d
```
