#!/bin/bash

TAG=$(git describe "${GITHUB_REF}")
TOPLEVEL=$(git rev-parse --show-toplevel)
git tag --list --format="%(subject)%0a%(body)" $TAG > release.md
echo "release_version=${TAG//v}" >> $GITHUB_ENV
echo "component=${basename $TOPLEVEL}" >> $GITHUB_ENV