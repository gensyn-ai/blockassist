#!/bin/bash

set -e -u
set -o pipefail

mkdir -p ~/.gradle

if [ ! -f "~/.gradle/gradle.properties" ]; then
    echo "Creating ~/.gradle/gradle.properties" >> logs/gradle_setup.log
    touch ~/.gradle/gradle.properties
fi

if grep -Fxq "org.gradle.daemon=true" "$HOME/.gradle/gradle.properties"; then
    echo "Gradle daemon setting already exists" >> logs/gradle_setup.log
else
    echo "Adding gradle daemon setting" >> logs/gradle_setup.log
    echo "org.gradle.daemon=true" >> ~/.gradle/gradle.properties;
fi
