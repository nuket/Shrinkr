#!/bin/bash

set -u
IFS=$'\n'

FILES=`ls -1 *.mp4`

for f in $FILES; do
    if [[ "$f" != *"-archive"* ]]; then
        A=${f%%.*}
        B=${f#*.}

        touch -r "${f}" "${A}-archive.${B}"
    fi
done
