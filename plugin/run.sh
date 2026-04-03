#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export JAVA_HOME="$(brew --prefix openjdk@21)/libexec/openjdk.jdk/Contents/Home"
./gradlew run
