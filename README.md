# Env-Helper

A Django-based web application for managing and controlling development environments using Docker containers. This tool allows users to create, manage, and control various types of development environments including VSCode and Docker Webtop instances.

## Features

- Create and manage multiple development environments
- Support for different environment types:
  - VSCode (code-server)
  - Docker Webtop (Ubuntu KDE)
  - Custom environments
- Container management with:
  - Port mapping
  - Volume mounting
  - Environment variables
  - Resource limits (CPU and Memory)
  - Auto-start capabilities
- RESTful API for environment management
- Web interface for easy environment control

## Requirements

- Docker
- Docker Compose
- Other dependencies are handled by Docker

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Dvaita-Tech/env-helper.git
   cd env-helper
   ```

2. Configure environment variables in `.env` file:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   POSTGRES_NAME=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=db
   ```

## Usage

The project uses Docker Compose to run all required services, making it easy to get started without installing dependencies locally.

Start the application:
```bash
docker compose up -d
```

This will:
- Start a PostgreSQL database
- Run migrations automatically
- Start the Django application server
- Set up Traefik as reverse proxy
- Mount local directory for live code changes

Access the application:
- Web Interface: http://localhost
- Traefik Dashboard: http://localhost:8080

To view logs:
```bash
docker compose logs -f
```

To stop the application:
```bash
docker compose down
```

## Testing

Run the test suite:
```bash
docker compose run --rm web pytest
```

## License

[Add License Information]

## Contributing

[Add Contributing Guidelines]
