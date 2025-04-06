FROM alpine:latest

# Install necessary dependencies (add more as needed)
RUN apk update && \
    apk add --no-cache \
    build-base \
    curl \
    wget \
    git \
    python3 \
    py3-pip \
    vim \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Set the working directory in the container
WORKDIR /Hunt-Bot

COPY . /Hunt-Bot
RUN pip3 install --no-cache-dir -r requirements.txt
# Set the default command to run when the container starts
CMD ["python3", "main.py"]
