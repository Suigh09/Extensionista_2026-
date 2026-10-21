FROM python:3.11.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app
COPY requirements.txt ./
RUN pip install --requirement requirements.txt
COPY backend ./backend
RUN chown -R app:app /app
USER app
WORKDIR /app/backend
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
