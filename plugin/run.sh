#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export RAGGER_PROJECT_ROOT="$(cd .. && pwd)"
./gradlew run
