.DEFAULT_GOAL := help
IMAGE ?= ghcr.io/abhisheksawant52/argocd-gitops-platform
TAG ?= 0.1.0

.PHONY: help install lint format test build docker clean validate

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

lint: ## Run ruff and black in check mode
	ruff check src tests
	black --check src tests

format: ## Auto-format the codebase
	ruff check --fix src tests
	black src tests

test: ## Run the test suite
	pytest

validate: ## Validate all Kubernetes/ArgoCD manifests are well-formed YAML
	python -c "import sys, glob, yaml; [list(yaml.safe_load_all(open(f, encoding='utf-8'))) for f in glob.glob('**/*.yaml', recursive=True)]; print('manifests OK')"

build: ## Build the Python distribution artifacts
	python -m pip install --upgrade build
	python -m build

docker: ## Build the container image
	docker build -t $(IMAGE):$(TAG) .

clean: ## Remove build and cache artifacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
