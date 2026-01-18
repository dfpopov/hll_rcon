#!/bin/bash
# publish-docker.sh - Скрипт для публикации Docker образов с автоматическим версионированием

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для получения последней версии из Docker Hub
get_latest_version() {
    local repo=$1
    local api_url="https://hub.docker.com/v2/repositories/${repo}/tags/?page_size=100&ordering=-last_updated"
    
    # Получаем все теги и фильтруем только версии (vX.Y.Z или X.Y.Z)
    local versions=$(curl -s "${api_url}" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | \
        grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
    
    echo "$versions"
}

# Функция для увеличения патч-версии
increment_patch_version() {
    local version=$1
    
    # Убираем префикс 'v' если есть
    local clean_version=${version#v}
    
    # Разбиваем на части
    IFS='.' read -r major minor patch <<< "$clean_version"
    
    # Увеличиваем патч-версию
    patch=$((patch + 1))
    
    # Формируем новую версию с префиксом 'v' если был
    if [[ $version == v* ]]; then
        echo "v${major}.${minor}.${patch}"
    else
        echo "${major}.${minor}.${patch}"
    fi
}

# Парсинг аргументов
USERNAME=${2:-"dinnamo1927"}  # По умолчанию используется текущий username
BACKEND_REPO="${USERNAME}/hll_rcon_tool"
FRONTEND_REPO="${USERNAME}/hll_rcon_tool_frontend"

# Определяем тег
if [ -z "$1" ] || [ "$1" == "auto" ] || [ "$1" == "++" ]; then
    # Автоматическое определение версии
    echo -e "${BLUE}🔍 Поиск последней версии...${NC}"
    LATEST_VERSION=$(get_latest_version "$BACKEND_REPO")
    
    if [ -z "$LATEST_VERSION" ]; then
        # Если версий нет, начинаем с v1.0.0
        NEW_TAG="v1.0.0"
        echo -e "${YELLOW}⚠️  Версии не найдены, начинаем с v1.0.0${NC}"
    else
        NEW_TAG=$(increment_patch_version "$LATEST_VERSION")
        echo -e "${GREEN}📌 Последняя версия: ${LATEST_VERSION}${NC}"
        echo -e "${GREEN}📌 Новая версия: ${NEW_TAG}${NC}"
    fi
    TAG=$NEW_TAG
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Использование: $0 [tag|auto|++] [username]"
    echo ""
    echo "Параметры:"
    echo "  tag      - Конкретный тег для публикации (например: v1.0.0)"
    echo "  auto     - Автоматически увеличить патч-версию от последней"
    echo "  ++       - То же что и auto"
    echo "  username - Docker Hub username (по умолчанию: dinnamo1927)"
    echo ""
    echo "Примеры:"
    echo "  $0              # Автоматически увеличить версию"
    echo "  $0 auto         # Автоматически увеличить версию"
    echo "  $0 v1.0.5       # Опубликовать конкретную версию"
    echo "  $0 auto dfpopov # Автоматически с другим username"
    exit 0
else
    # Использовать указанный тег
    TAG=$1
fi

echo ""
echo -e "${GREEN}🚀 Публикация Docker образов${NC}"
echo -e "Tag: ${YELLOW}${TAG}${NC}"
echo -e "Backend: ${YELLOW}${BACKEND_REPO}${NC}"
echo -e "Frontend: ${YELLOW}${FRONTEND_REPO}${NC}"
echo ""

# Проверка входа в Docker Hub
# Проверяем, что Docker доступен
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Ошибка: Docker не запущен или недоступен${NC}"
    exit 1
fi

# Проверяем наличие авторизации в конфиге Docker
# Пропускаем проверку, так как docker buildx сам проверит авторизацию при push
# Если авторизации нет, buildx выдаст ошибку с понятным сообщением

# Создать buildx builder если не существует
if ! docker buildx ls | grep -q "multiarch"; then
    echo -e "${YELLOW}📦 Создание buildx builder...${NC}"
    docker buildx create --name multiarch --use
fi

# Установить buildx как активный
docker buildx use multiarch

# Собрать и опубликовать backend
echo -e "${GREEN}🔨 Сборка backend образа...${NC}"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t "${BACKEND_REPO}:${TAG}" \
    -t "${BACKEND_REPO}:latest" \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend образ опубликован${NC}"
else
    echo -e "${RED}❌ Ошибка при публикации backend образа${NC}"
    exit 1
fi

# Собрать и опубликовать frontend
echo -e "${GREEN}🔨 Сборка frontend образа...${NC}"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f Dockerfile-frontend \
    -t "${FRONTEND_REPO}:${TAG}" \
    -t "${FRONTEND_REPO}:latest" \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend образ опубликован${NC}"
else
    echo -e "${RED}❌ Ошибка при публикации frontend образа${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Все образы успешно опубликованы!${NC}"
echo ""
echo "Проверить на Docker Hub:"
echo "  - https://hub.docker.com/r/${BACKEND_REPO}"
echo "  - https://hub.docker.com/r/${FRONTEND_REPO}"
echo ""
echo "Использовать в docker-compose:"
echo "  BACKEND_DOCKER_REPOSITORY=${BACKEND_REPO}"
echo "  FRONTEND_DOCKER_REPOSITORY=${FRONTEND_REPO}"
echo "  TAGGED_VERSION=${TAG}"
