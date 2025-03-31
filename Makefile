# Determine which docker compose command to use
DOCKER_COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo docker-compose; else echo "docker compose"; fi)

.PHONY: run stop test try

start:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
	fi
	@echo "Using docker compose command: $(DOCKER_COMPOSE)"
	$(DOCKER_COMPOSE) build
	$(DOCKER_COMPOSE) up -d

stop:
	@echo "Using docker compose command: $(DOCKER_COMPOSE)"
	$(DOCKER_COMPOSE) down

test:
	@echo "Running tests..."
	pytest tests/ -v --asyncio-mode=auto 

try:
	@echo "Making 5 parallel requests to the /generate endpoint..."
	@echo "----------------------------------------"
	@( \
		for i in {1..5}; do \
			curl -N -X POST http://localhost:8000/generate \
				-H "Content-Type: application/json" \
				-d "{\"prompt\": \"Request $$i: Write a creative short story about a robot learning to paint.\"}" & \
		done; \
		echo "----------------------------------------"; \
		echo "All requests submitted. Watch the output above to see parallel processing in action."; \
		echo "Press Ctrl+C to stop watching the output."; \
		wait \
	)