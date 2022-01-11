# Description

This contains a simple implementation of a sublime build system for matter

# Installation

Ensure you have a dockerfile prepared based on chip-build-vscode. 
Something like below (with the proper github checkout path set):

```
docker run --name bld_vscode --volume $HOME/devel/connectedhomeip:/workspace connectedhomeip/chip-build-vscode:0.5.43 -it /bin/bash
```

Then install:

```
ln -s ./matter_build.py ~/.config/sublime-text/Packages/User/
ln -s ./MatterDockerBuild.sublime-build.py ~/.config/sublime-text/Packages/User/
```

Setup a build system in your project, like:

```
  //...
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
