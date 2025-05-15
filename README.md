# Introduction

This repository is for the source code of the NOVA dashboard (running at https://nova.ornl.gov). The dashboard provides a
way for users to launch interactive tools without going through Calvera.

## Install dependencies

You will need to install [Poetry](https://python-poetry.org/) and [pnpm](https://pnpm.io/). After doing so, you can run
the following commands to build the source code.

```bash
poetry install
poetry run ./manage.py migrate
```

```bash
cd src/vue
pnpm i
```

## Run

To configure and run the app properly, a `.env` file is needed in the top level directory of this repository.
A sample file `.env.sample` is provided that describes the available configuration options. Because your `.env` may contain
secrets, make sure this does not get committed to the upstream repository. You can also set the environment variables
manually in your environment or prefix them to your run command.

When setting your environment variables, please download https://nova-test.ornl.gov/tools.json
and ensure that `NOVA_TOOLS_PATH` points to it.

After your environment is configured, run the following to start the client:

```bash
cd src/vue
pnpm run dev --host 0.0.0.0 --port 5173
```

After that to start the application (from the root directory):

```bash
poetry run ./manage.py runserver_plus --insecure 0.0.0.0:8080
```

## Develop

Run `poetry env info  --path` to see the path to Poetry environment. It can then be used
to configure your IDE to select the correct Python interpreter.

## Docker

### Build the image

without conda and mantid:

```bash
docker build . -f dockerfiles/Dockerfile -t app --platform {your_build_platform}
```

### Run the container

```bash
docker run -p 8080:8080 -it --env-file {path/to/your/.env} app
```

then open your browser at http://localhost:8080
