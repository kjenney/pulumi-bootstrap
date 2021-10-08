FROM python:3.8.11-slim

ENV PATH="$PATH:/root/.pulumi/bin"

RUN apt update && \
    apt install -y curl gcc && \
    apt clean
RUN curl -fsSL https://get.pulumi.com | sh

COPY requirements.txt .
RUN pip install -r requirements.txt