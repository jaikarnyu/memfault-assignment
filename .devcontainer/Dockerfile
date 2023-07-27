# Image for a Python 3 development environment
FROM python:3.9-slim

# Add any tools that are needed beyond Python 3.9
RUN apt-get update && \
    apt-get install -y sudo vim make git zip tree curl wget jq && \
    apt-get autoremove -y && \
    apt-get clean -y

# Create a user for development
ARG USERNAME=webbot
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user with passwordless sudo privileges
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash \
    && usermod -aG sudo $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Added libraries for PostgreSQL
RUN apt-get update && apt-get install -y gcc libpq-dev

# Set up the Python development environment
WORKDIR /app
RUN python -m pip install --upgrade pip wheel

ENV PORT 8080
EXPOSE $PORT

# Enable color terminal for docker exec bash
ENV TERM=xterm-256color
ENV aws_access_key_id=AKIAUXHD6LSDRNOOLW7Z
ENV aws_secret_access_key=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
ENV aws_region=us-east-1
ENV aws_s3_bucket=webbotexperiments

# Become a regular user
USER $USERNAME