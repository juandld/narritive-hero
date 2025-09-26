SHELL := /bin/bash

.PHONY: test backend-test

test: backend-test ## Run all tests
	@echo "Done."

backend-test: ## Run backend tests
	@chmod +x backend/test.sh || true
	@backend/test.sh

