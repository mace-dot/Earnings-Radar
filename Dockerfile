FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    RADAR_REQUIRE_AUTH=true \
    EARNINGS_RADAR_DB_PATH=/var/lib/earnings-radar/earnings_radar.db \
    RADAR_RESEARCH_DB_PATH=/var/lib/earnings-radar/research.db \
    EARNINGS_RADAR_EXPORTS_DIR=/var/lib/earnings-radar/exports
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
COPY . ./
RUN mkdir -p /var/lib/earnings-radar
EXPOSE 8501
CMD ["python", "-m", "earnings_radar.hosting"]
