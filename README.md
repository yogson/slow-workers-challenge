# Slow Workers Challenge

A service that demonstrates parallel processing of text generation requests using Redis queues and workers.

## Prerequisites

- Docker and Docker Compose
- Make

## Quick Start

1. Start the service:
```bash
make start
```
This will:
- Create a `.env` file from `.env.example` if it doesn't exist
- Build and start the Docker containers (API, worker, and Redis)

2. Stop the service:
```bash
make stop
```
This will stop and remove all Docker containers.

3. Run tests:
```bash
make test
```
This will run the test suite using pytest.

4. Try parallel processing:
```bash
make try
```
This will:
- Make 5 parallel requests to the `/generate` endpoint
- Show real-time streaming responses from all requests
- Demonstrate parallel processing in action
- Press Ctrl+C to stop watching the output

## Environment Variables

The service uses the following environment variables (configured in `.env`):
- `API_PORT`: Port for the API service (default: 8000)
- `REDIS_URL`: Redis connection URL
- `REDIS_QUEUE_NAME`: Name of the Redis queue for jobs
- `LOG_LEVEL`: Logging level for services
- `BATCH_WINDOW_MS`: Time window for batching requests
- `MAX_REQUESTS_PER_JOB`: Maximum requests per job batch


---
## Informal section

In this section, I will describe solution architecture decisions, concerns, and TODOs.

### Intro

The solution's appearance is mainly influenced by the central idea: we shall consider this solution as a PoC, not a production application, not even an MVP.
This consideration determines the project layout, code completeness, runtime environment configuration, and many more.

### Architecture

The service consists of three main components:
- API service: Handles incoming requests and streams responses
- Worker service: Processes requests in parallel
- Redis: Manages job queues and stores responses

#### API service

This project is not intended to be a big API solution, so I chose a simple async microframework - aiohttp. 
We don't need integrated serialization, database access management, and so on; we just need to process requests and stream responses.

#### Worker service

The slow workers problem is not something new; we don't need to reinvent the wheel because there are many ready-to-use solutions in the Python world. 
The common choice is Celery, but for our service, I use a more simple and straightforward Redis Queue (RQ). This solution handles job offloading and background processing.
The job worker is implemented in an async way, so it may process more than one request in each job to be used for batch processing.
The worker service is designed to be scalable. We just need to set more workers count in the config to scale it up. 

#### Redis

We use Redis as an exchange point between the API and workers. 

### Considerations and future refinements

Despite the PoC nature, the project is shaped to be modular and extendable. The key points are:
* Aligning with best practices and SOLID principles, the project is modular and each module can be substituted. For example, there is no need to touch the API or jobs manager to replace Redis with another data exchange service.
* The data package contains a data interaction interface which may be implemented using other media as a data-exchange point. For now, we have implemented a Redis interactor, but we can decide to replace it with, for example, Kafka Streams.
* The job manager is the central part of the project, and it can use any other compatible media as a queue.
* The API module can be parametrized with various compatible data interactors with no need to change the code of the API.

As for the future of the project, I may suggest:
* Adding more unit tests and introducing integration tests
* Splitting the project to get more value from parallel development. The project is structured in a way that allows us to independently develop the API, data interaction/integration, workers, and jobs management.
* Deploying the components in a Kubernetes environment to get its benefits like seamless deployment and autoscaling.
* Adding more observability: tracing, metrics, enhanced logging.
* If heavy load appears, in addition to scaling, we can improve performance by optimizing, for example, Redis data querying. There is a potential improvement in how we query for request data and its status, which can be queried simultaneously. 



