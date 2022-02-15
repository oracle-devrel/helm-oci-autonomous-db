FROM python:3
ADD check_autodb.py /
RUN apt update && \
    apt install -y curl && \
    curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && \
    curl -LO https://dl.k8s.io/release/v1.23.0/bin/linux/amd64/kubectl &&\
    chmod +x kubectl && \
    mv ./kubectl /usr/local/bin/kubectl


