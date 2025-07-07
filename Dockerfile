# Базовый Python-образ
FROM python:3.10-slim

# Установка рабочей директории
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Объявляем директорию с данными (CSV-файл логов)
VOLUME ["/app/data"]

# Стартовая команда
CMD ["python", "main.py"]