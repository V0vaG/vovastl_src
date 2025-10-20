FROM python:3.10-slim

ARG VERSION
ENV VERSION=$VERSION

ARG B_NUM
ENV B_NUM=$B_NUM

ARG BRANCH
ENV BRANCH=$BRANCH

# Install system dependencies required for CadQuery
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/* \
    || (apt-get update && apt-get install -y \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/*)

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--timeout", "120", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

