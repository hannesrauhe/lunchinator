#!/bin/bash

# check if building a Tag or a regular branch
VERSION="$(git describe --tags --abbrev=0).$(git rev-list HEAD --count)"
TAG=true

