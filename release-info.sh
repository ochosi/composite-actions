#!/bin/bash

TAG=$(git describe "${GITHUB_REF}")
git tag --list --format="%(subject)%0a%(body)" $TAG > release.md
echo "release_version=${TAG//v}" >> $GITHUB_ENV