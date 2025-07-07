FROM public.ecr.aws/docker/library/python:3.11-slim AS base

# Debug tools
RUN apt-get update -y && apt-get install -y curl postgresql-client git
COPY ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt
WORKDIR /app

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY controller.py main.py demo.py models-extra-info.toml /app/
# Useful for export scripts
COPY utils /app/utils
COPY templates /app/templates
COPY assets /app/assets
COPY languia /app/languia
