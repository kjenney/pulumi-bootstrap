FROM python:3.8.11-slim

ENV PATH="$PATH:/root/.pulumi/bin"
ENV WORKINGDIR="/bootstrap"
ENV PYTHONPATH="$WORKINGDIR/modules"

WORKDIR ${WORKINGDIR}

RUN apt update && \
    apt -qy full-upgrade && \
    apt install -y curl gcc git && \
    apt clean
RUN curl -fsSL https://get.pulumi.com | sh
RUN curl -fsSL https://get.docker.com/ | sh

COPY requirements.txt .
RUN pip install -r requirements.txt
