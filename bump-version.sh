#!/bin/bash

sed -i -E "s/(Version:\\s+)[0-9].+/\1$1/" osbuild*.spec

if [ -f "setup.py" ]; then
  sed -i -E "s/(version=\")[0-9]+/\1$1/" setup.py
fi
