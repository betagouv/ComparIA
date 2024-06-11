FROM python:3.9-slim

RUN groupadd fastchat --gid 10001 && useradd --system -u 10001 --gid 10001 --home /app fastchat
USER fastchat
WORKDIR /app

# Install deps first
RUN pip3 install fschat[webui,model_worker]

# For monitoring
RUN pip3 install plotly

# For OpenAI-like APIs
RUN pip3 install openai

COPY --chown=fastchat:fastchat . /app
