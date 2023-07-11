 # python based docker builder
 
this projects manages and builds docker compose files given the specification of:

 - 1 front facing nginx frontend server
 - many different backend servers
 - each backend is accessible through <server>/api/<backendname>

## setup

 - Make sure a ssh key (pair (id_rsa / id_rsa.pub)) is added to `/build-dockers/local/ssh`. 
The ssh is used to communicate with the git repository.
Add the git repository to `known_hosts` file in the above directory
 - activate the virtual environment and instal the libraries from the requirements.txt
 - verify by running `python main.py -h`
 - Whenever you run a command expect a password is required to be provided.
this is to make the script run as root for docker priveleges.


## Create
Example: `python main.py dockers/testproject create --branch production ssh://git@git.example.server`

This creates a network group for "testproject", it adds the docker compose to the `./dockers/testproject`.
Then creates a frontend server called "nginx" (actual docker name: testproject.nginx) with data stored inside `dockers/testproect/testproject.nginx/`
The script downloads from git.example.server using the credentials provided in the `build-dockers/local/ssh` directory,  Using the branch production.

```
usage: main.py directory create [-h] [--network NETWORK] [-p PORT] [--branch BRANCH] [--build-env BUILD_ENVIRONMENT_VARIABLES] [--overwrite] [-e ENVIRONMENT_VARIABLES] [--yaml YAML] git

positional arguments:
  git                   Git repository of frontend

options:
  -h, --help            show this help message and exit
  --network NETWORK     New network name
  -p PORT, --port PORT  New network port
  --branch BRANCH       branch or tag from where to clone
  --build-env BUILD_ENVIRONMENT_VARIABLES
                        Environment variable during build
  --overwrite           Overwrite existing dockers
  -e ENVIRONMENT_VARIABLES
                        Environment variable for new docker container
  --yaml YAML           Yaml settings for frontend service
```


## Add backend

Example: `python main.py dockers/testproject add --branch production --yaml dockers/testproject.core.yml core ssh:git.example.server`

This adds a new backend, nodejs server with the name "core" to the group 'testproject'.
The build data will be stored inside `dockers/testproject/testproject.core` directory, and the docker will have as name `testproject.core`

The script downloads from git.example.server using the credentials provided in the `build-dockers/local/ssh` directory, using the branch production.


```
usage: main.py directory add [-h] [--branch BRANCH] [--url-path URL_PATH] [--port PORT] [--yaml YAML] [--server-type {node,nginx}] [--node-version NODE_VERSION] [-v VOLUMES] [-e ENVIRONMENT_VARIABLES]
                             [--build-env BUILD_ENVIRONMENT_VARIABLES]
                             docker git

positional arguments:
  docker                New docker name
  git                   Git repository

options:
  -h, --help            show this help message and exit
  --branch BRANCH       branch or tag from where to clone
  --url-path URL_PATH   path to connect to the server
  --port PORT           Port docker uses internally
  --yaml YAML           Yaml settings for service
  --server-type {node,nginx}
                        Server type to use
  --node-version NODE_VERSION, --version NODE_VERSION
                        Server version to use
  -v VOLUMES            Volume for new docker container
  -e ENVIRONMENT_VARIABLES
                        Environment variable for new docker container
  --build-env BUILD_ENVIRONMENT_VARIABLES
                        Environment variable during build
```


## Update
Example: `python main.py dockers/testproject update core`

This will update the "core" backend server (note that only `core` is supplied and not the docker name `testproject.core`).
The parameter `--branch` can be given to update from a specific branch. If it is omited it will use last used branch. 
Supplying branch is useful when wishing to change branches. Or one can provide a specific tag/commit id so the server can be rolled back to a working version.

```
 python main.py dockers/test update -h
usage: main.py directory update [-h] [--git GIT] [--branch BRANCH] [docker ...]

positional arguments:
  docker           Docker container name

options:
  -h, --help       show this help message and exit
  --git GIT        Git repository
  --branch BRANCH  branch or tag from where to clone, if not given same branch as existing code is used
```


## Reload
Example: `python main.py dockers/testproject reload --yaml dockers/testproject.core.yml core`

This reloads the settings from the given yaml file for the `core` project and updates the dockers. Without downloading the code or compiling the source.
Useful for updating environment variables for example.

```
usage: main.py directory reload [-h] [--yaml YAML] [-v VOLUMES] [-e ENVIRONMENT_VARIABLES] [-f] docker

positional arguments:
  docker                Docker container name

options:
  -h, --help            show this help message and exit
  --yaml YAML           Yaml settings for docker service
  -v VOLUMES            Volume for new docker container
  -e ENVIRONMENT_VARIABLES
                        Environment variable for new docker container
  -f, --forced          Force rebuilding of all dockers upon loading
```

## Remove

Example: `python main.py dockers/testproject remove --clean core`

This will remove the `core` backend server from the project. Allowing a clean rebuild.
It is highly recommended to always provide the `--clean` argument, so that the actual docker also gets removed, as well as the reverse proxy updated.

This cannot be used to remove the frontend/proxy server, for that use the purge command.


```
usage: main.py directory remove [-h] [-c] docker

positional arguments:
  docker       Docker name

options:
  -h, --help   show this help message and exit
  -c, --clean  Clean reverse proxy
```


## Purge
Example: `python main.py dockers/testproject purge --force`

This will remove the whole project `testproject`, including all containers and the reverse proxy/frontend. 
Use `--force` to prevent errors if there are still dockers running. 

```
usage: main.py directory purge [-h] [-f]

options:
  -h, --help   show this help message and exit
  -f, --force  Forcibly remove managed networks
```

## Rebuild protal
Example: `python main.py dockers/testproject rebuild-protal`

This is used to rebuild the reverse proxy, in case there are updated backend servers which are not included in the proxy.
Ie if servers got removed without adding --clean. Or servers got renamed.

```
usage: main.py directory rebuild-portal [-h]

options:
  -h, --help  show this help message and exit
```

## list
Example `python main.py dockers/testproject ls`

List information about the servers in a project, the current git commit as well as the branch the project is follwoing

```
usage: main.py directory ls [-h]

options:
  -h, --help  show this help message and exit
```

## yaml file

A few commands allow to specify a yaml configuration file. In principle this file follow the format of docker-compose.yml.
This file is inserted into the docker compose "under" `service.dockername`.

Of importance are the environment variables, those combine with the configuration loader script in javascript and can be used to provide secret data.
Environment variables that should be visible to the application should start with `SERVER__CONFIG__`

As specified in that library, the environment variables use two underscores `__` to go one level deeper into the directory tree.
For example the hostname for a postgres server (and identified by `main`) would be:

```yaml
SERVER__CONFIG__datastores__main__host: my.example.com
SERVER__CONFIG__datastores__main__port: 5432
```

An example file:
```yaml
restart: 'unless-stopped'
environment:
  SERVER__CONFIG__datastores__main__host: my.example.com
  SERVER__CONFIG__datastores__main__port: 5432
  SERVER__CONFIG__datastores__main__user: user
  SERVER__CONFIG__datastores__main__password: password
  SERVER__CONFIG__datastores__main__database: some_database
  SERVER__CONFIG__server__ROOT_KEY: secretkey
  SERVER__CONFIG__server__session__secret: secretsessionkey
```
