#!/bin/bash

set -e -u
set -o pipefail

ROOT="$PWD"

source ./scripts/node_env.sh

cd modal-login

if [ ! -d .next ]; then
    ### Install Node, NVM, Yarn if needed.
    setup_node_nvm

    ### Setup environment configuration
    setup_environment

    echo "Installing dependencies..." >> logs/yarn_setup.log
    yarn install --immutable

    echo "Building server..." >> logs/yarn_setup.log
    yarn build

fi