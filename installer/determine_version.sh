#!/bin/bash

# check if building a Tag or a regular branch
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" == "HEAD" ]
then
  # detached state, get tag version
  VERSION="$(git describe --tags --abbrev=0)"
  TAG=true
else
  # building unstable version
  TAG=false
  VERSION="$(git describe --tags | sed -e "s/^\\([^.]*\\.[^.]*\\.\\).*/\\1$(git rev-list HEAD --count).${BRANCH}/")"
  echo -e "\e[00;31m***** WARNING: Building unstable release ${VERSION} *****\e[00m"
fi

