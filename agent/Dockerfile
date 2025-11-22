
FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

ENV FOUNDRY_DIR="/root/.foundry"
ENV PATH="$FOUNDRY_DIR/bin:$PATH"
RUN curl -L https://foundry.paradigm.xyz | bash && foundryup

RUN pip install slither-analyzer solc-select
RUN solc-select install 0.8.20 && solc-select use 0.8.20

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["./run_agent.sh"]
