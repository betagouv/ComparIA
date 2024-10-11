FROM python:3-slim
RUN pip install uvicorn geoip2 fastapi
COPY ./GeoLite2-City.mmdb .
COPY ./geoip.py .
CMD uvicorn geoip:app --host 0.0.0.0 --port 8000