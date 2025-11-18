# Tech Forum Monitor Backend

Backend service for aggregating tech forum topics, exposing a FastAPI interface, and orchestrating Celery-based background jobs for RSS ingestion.

## Features

- FastAPI backend for serving data.
- Celery for asynchronous task processing (RSS fetching).
- PostgreSQL database for data storage.
- Redis for Celery message broking and results backend.
- Alembic for database migrations.
- Docker Compose for easy local development setup.

## Getting Started

Follow these instructions to get the project up and running on your local machine for development and testing purposes.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation & Setup

1.  **Build and run services with Docker Compose**

    This command will build the Docker images and start all the services (backend, database, redis, celery worker, and celery beat) in detached mode.
    ```bash
    docker-compose up -d --build
    ```

2.  **Apply database migrations**

    Once the services are running, apply the database migrations to create the necessary tables.
    ```bash
    docker-compose exec backend alembic upgrade head
    ```

The application should now be running and accessible. The FastAPI service is available at `http://localhost:8000`.

## How to Check the Fetched Data

The fetched posts are stored in a PostgreSQL database in the `posts` table. You can inspect the data directly by connecting to the database container.

1.  **Access the PostgreSQL container**

    Use `docker-compose exec` to get a shell inside the running `postgres` container.
    ```bash
    docker-compose exec postgres bash
    ```

2.  **Connect to the database using psql**

    Inside the container, connect to the `tech_forum_monitor` database using the `psql` client. The credentials are set in the `docker-compose.yml` file.
    ```bash
    psql -U postgres -d tech_forum_monitor
    ```
    *(Default user: `postgres`, database: `tech_forum_monitor`)*

3.  **Query the data**

    Once connected, you can run standard SQL queries.

    - To list all tables:
      ```sql
      \dt
      ```
    - To view the 10 most recent posts:
      ```sql
      SELECT * FROM posts ORDER BY published_at DESC LIMIT 10;
      ```
    - To exit the `psql` client, type `\q`.
