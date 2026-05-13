# Makefile for asr2clip pip package

# Variables
PACKAGE_NAME := asr2clip
DIST_DIR := dist
BUILD_DIR := build
SRC_DIR := asr2clip

# Default target
all: build

# ── Code quality ──────────────────────────────────────────────────

# Run all checks (mirrors CI)
check: lint format-check typecheck complexity

# Lint with ruff
lint:
	ruff check $(SRC_DIR)/

# Auto-format with ruff
format:
	ruff check --fix $(SRC_DIR)/
	ruff format $(SRC_DIR)/

# Check formatting without modifying files
format-check:
	ruff format --check $(SRC_DIR)/

# Type check with ty
typecheck:
	ty check

# Cyclomatic complexity check
complexity:
	complexipy $(SRC_DIR)/ -e "_vendor"

# ── Packaging ─────────────────────────────────────────────────────

# Build the package
build:
	@echo "Building $(PACKAGE_NAME)..."
	python -m build
	@echo "Build complete. Distribution files are in $(DIST_DIR)/"

# Push the package to PyPI
push:
	@echo "Pushing $(PACKAGE_NAME) to PyPI..."
	twine upload $(DIST_DIR)/*
	@echo "Package pushed to PyPI."

# Clean up build and distribution files
clean:
	@echo "Cleaning up build and distribution files..."
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info
	@echo "Cleanup complete."

# ── Help ──────────────────────────────────────────────────────────

help:
	@echo "Available targets:"
	@echo ""
	@echo "  Code quality:"
	@echo "    check        - Run all checks (lint + format-check + typecheck + complexity)"
	@echo "    lint         - Lint with ruff"
	@echo "    format       - Auto-fix lint issues and format code"
	@echo "    format-check - Check formatting without modifying files"
	@echo "    typecheck    - Type check with ty"
	@echo "    complexity   - Cyclomatic complexity check with complexipy"
	@echo ""
	@echo "  Packaging:"
	@echo "    build        - Build the pip package"
	@echo "    push         - Push the package to PyPI"
	@echo "    clean        - Clean up build and distribution files"

.PHONY: all check lint format format-check typecheck complexity build push clean help
