#!/usr/bin/env bash

ISORT_ARGS="-c django_comments_ink"
BLACK_ARGS="--check django_comments_ink"

# Check number of variable parameters passed to the script.
if [[ $# -ne 1 ]]; then
    echo "Usage: lint.sh [check|format]"
    exit 1
elif [[ $1 != "check" ]] && [[ $1 != "format" ]]; then
    echo "Usage: lint.sh [check|format]"
    exit 1
else
    if [[ $1 == "format" ]]; then
        ISORT_ARGS="django_comments_ink"
        BLACK_ARGS="django_comments_ink"
    fi
fi

echo "Running: isort ${ISORT_ARGS}"
isort ${ISORT_ARGS}
if [ $? -ne 0 ]; then
    exit 1
fi

echo "Running: black ${BLACK_ARGS}"
black ${BLACK_ARGS}
