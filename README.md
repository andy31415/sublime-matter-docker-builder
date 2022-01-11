# Description

This contains a simple implementation of a sublime build system for matter

# Installation

Ensure you have a dockerfile prepared based on chip-build-vscode. 
Note that this uses [podman](https://podman.io) for easier control of permissions (don't want to output files owned by root).

```sh
podman run --privileged -dt                                   \
    --storage-opt overlay.ignore_chown_errors=true            \
    --name bld_vscode                                         \
    --volume $HOME/devel/connectedhomeip:/workspace           \
    docker.io/connectedhomeip/chip-build-vscode:0.5.43        \
    /bin/bash
```

Note the `ignore_chown_errors` flag: I have not been able to actually fetch
the vscode image without it, but it also means some uid mappings will not be
enforced in the container  (may not matter much as we want a regular user build).

Then install:

```sh
ln -s ./matter_build.py ~/.config/sublime-text/Packages/User/
ln -s ./MatterDockerBuild.sublime-build.py ~/.config/sublime-text/Packages/User/
```

Setup a build system in your project, like:

```json
  "build_systems": [
     {
         "name": "Matter Docker Build",
         "target": "matter_docker_build",
     },
     {
         "name": "Matter Docker Build - KILL",
         "target": "matter_docker_build",
         "kill": true,
     }
  ]
```
