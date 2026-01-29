# Makefile for asr2clip pip package

# Variables
PACKAGE_NAME := asr2clip
DIST_DIR := dist
BUILD_DIR := build

# Default target
all: build

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

# Help target
help:
	@echo "Available targets:"
	@echo "  build   - Build the pip package"
	@echo "  push    - Push the package to PyPI"
	@echo "  clean   - Clean up build and distribution files"
	@echo "  help    - Show this help message"

.PHONY: all build push clean help
