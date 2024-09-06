Python project template
=======================

# Introduction

This repository is a template repository for Python projects for NDIP (and, in the future, NOVA).
After you create a new repository using this repo as template, please adjust it for the new project.

-  Change the name of the package in `pyproject.toml` and rename `/src/app`folder.
- Add other Python dependencies you project need `poetry add xxx` or `poetry add --dev xxx`
- Modify Dockerfile as needed. Please make sure it can still run as non-root (we use it in GitLab CI/CD and in general this
is a good practice).
- install pre-commit (if not already installed) - `pip install pre-commit`
- activate `pre-commit` for your project: `cd <project folder> && pre-commit install`
- finally, clear the content of this section and add the description of your project. You can keep/adjust instructions
below

Note 1: please don't change linter settings, license, code of conduct without discussing with the team first - we want to keep them
the same for all out projects.

Note 2: if you think some changes that you've made might be useful for other projects as well, please fill free
to create an issue [in this repo](https://code.ornl.gov/ndip/project-templates/python/-/issues/new)



## Installation
```commandline
pip install poetry
poetry install --no-root
```

## Running
### From source
```bash
poetry run app
```

### Using Docker
```bash
# build from source
docker build -f dockerfiles/Dockerfile -t app_image .
# run a container
docker run app
```

## Formatting
```commandline
poetry run ruff format
```

## Linting
```commandline
poetry run ruff check
poetry run mypy .
```

## Testing
```commandline
poetry run pytest
```
or, with coverage
```commandline
poetry run coverage run
poetry run coverage report
```

## CI/CD in GitLab

Take a look at the `.gitlab-ci.yml` file. It configures pipelines to run in [GitLab](https://code.ornl.gov/ndip/project-templates/python/-/pipelines).
Some jobs will run automatically on each commit, jobs to
build packages and Docker images need to be trigerred manually. Don't forget to set versions properly:
in `pyproject.toml` for python package and in `.gitlab-ci.yml` for Docker tag.
