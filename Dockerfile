FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    netcat-traditional 
    # && mkdir -p /etc/apt/keyrings \
    # && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    # && echo \
    #     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    #     $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    # && apt-get update \
    # && apt-get install -y docker-ce-cli \
    # && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy wait-for-it script
COPY wait-for-it.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/wait-for-it.sh

# Copy project files
COPY . .

# No user change - keeping root as default
RUN touch debug.log
RUN chmod 666 debug.log

CMD ["sh", "-c", "wait-for-it.sh db:5432 && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
