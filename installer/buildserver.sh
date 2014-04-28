#!/bin/bash

cd $(dirname "$0")

if [ $(uname) == "Darwin" ]
then
  # ensure environment is fine (MacPorts and stuff)
  source ~/.profile
  source ~/.bash_profile
fi

function log() {
  echo "$@" | tee -a buildserver.log
}

function finish() {
  log "---------- Finished build at $(date) ----------"
  exit $1
}

log "---------- Starting build at $(date) ----------"

if [ "$1" == "" ]
then
  log "No command provided. Aborting." 1>&2
  finish 1
fi

# update Git
if ! git fetch
then
  log "Fetch failed." 1>&2
  finish 1
fi

# get latest tag version
CUR_TAG=$(git tag | tail -n 1)
if [ $? != 0 ] || [ "$CUR_TAG" == "" ]
then
  log "Could not determine latest tag version." 1>&2
  finish 1
fi

# get last build tag version
if [ -f .last-tag ]
then
  PREV_TAG=$(cat .last-tag)
fi

log "Current tag: $CUR_TAG"
log "Latest built tag: $PREV_TAG"

# check if there is a new tag
if [ "$CUR_TAG" != "$PREV_TAG" ]
then
  PREV_BRANCH=$(git symbolic-ref -q HEAD | cut -f 3 -d /)
  log "Checking out $CUR_TAG"
  if ! git checkout "$CUR_TAG"
  then
    log "Error checking out tag." 1>&2
    finish 1
  fi

  log "Building version $CUR_TAG"

  log "executing './$1' --publish"
  if eval "./$1 --publish" 2>&1 | tee -a buildserver.log
  then
    log "Successfully build version $CUR_TAG".
    echo "$CUR_TAG" >.last-tag
  fi

  log "Returning to branch $PREV_BRANCH"
  git checkout "$PREV_BRANCH"
else
  log "Versions identical, no need to build."
fi

finish 0
