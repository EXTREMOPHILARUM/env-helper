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

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/EXTREMOPHILARUM/env-helper.git
   cd env-helper
   ```

2. Create a `.env` file for development:
   ```bash
   cp .env.example .env
   ```

3. Configure environment variables in `.env` file:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   POSTGRES_NAME=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=db
   ```

4. Start the development environment:
   ```bash
   docker compose up -d
   ```

The development server will be available at `http://localhost:80`

## Production Deployment

1. Create production environment file:
   ```bash
   cp .env.prod.example .env.prod
   ```

2. Configure the production environment variables in `.env.prod`:
   ```
   # Django settings
   DJANGO_SECRET_KEY=<secure-secret-key>
   ALLOWED_HOSTS=your-domain.com
   DOMAIN=your-domain.com

   # Database settings
   POSTGRES_NAME=env_helper_prod
   POSTGRES_USER=env_helper_user
   POSTGRES_PASSWORD=<secure-password>

   # Let's Encrypt
   ACME_EMAIL=your-email@domain.com
   ```

3. Deploy using production compose file:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

The production server will be available at `https://your-domain.com`

### Production Features
- HTTPS support with automatic Let's Encrypt certificates
- Secure configuration with Traefik reverse proxy
- Database persistence
- Log rotation
- Health checks and automatic container restarts
- Multi-worker Gunicorn setup

## CI/CD Pipeline

The project includes automated CI/CD pipelines using GitHub Actions:

### Testing Pipeline
- Triggers on pull requests to main branch
- Runs the full test suite using pytest
- Ensures code quality before merging

### Docker Build Pipeline
- Triggers on:
  - Pushes to main branch
  - Release tags (v*.*.*)
- Builds and publishes Docker images to GitHub Container Registry
- Tags images with:
  - Latest tag for main branch
  - Version tags for releases (e.g., v1.0.0)

### Using Pre-built Images

You can use our pre-built Docker images from GitHub Container Registry:
```bash
docker pull ghcr.io/EXTREMOPHILARUM/env-helper:latest
```

Or specify a version:
```bash
docker pull ghcr.io/EXTREMOPHILARUM/env-helper:v1.0.0
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the terms of the license included in the repository.
