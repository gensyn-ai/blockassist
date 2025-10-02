#!/bin/bash

set -e -u
set -o pipefail

export SMART_CONTRACT_ADDRESS="0xE2070109A0C1e8561274E59F024301a19581d45c"
# Test if file exists, if so, source .env
if [[ -f "$PWD"/.env ]]; then
    source "$PWD"/.env
fi

# Function to setup Node.js and NVM
setup_node_nvm() {
    echo "Setting up Node.js and NVM..." >> logs/node_env.log

    if ! command -v node > /dev/null 2>&1; then
        echo "Node.js not found. Installing NVM and latest Node.js..." >> logs/node_env.log
        export NVM_DIR="$HOME/.nvm"
        if [ ! -d "$NVM_DIR" ]; then
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
        fi
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
        nvm install node
    else
        echo "Node.js is already installed: $(node -v)" >> logs/node_env.log
    fi

    if ! command -v yarn > /dev/null 2>&1; then
        # Detect Ubuntu (including WSL Ubuntu) and install Yarn accordingly
        if grep -qi "ubuntu" /etc/os-release 2> /dev/null || uname -r | grep -qi "microsoft"; then
            echo "Detected Ubuntu or WSL Ubuntu. Installing Yarn via apt..." >> logs/node_env.log

            curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
            echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
            sudo apt update && sudo apt install -y yarn
        else
            echo "Yarn not found. Installing Yarn globally with npm (no profile edits)…" >> logs/node_env.log
            # This lands in $NVM_DIR/versions/node/<ver>/bin which is already on PATH
            npm install -g --silent yarn
        fi
    fi
}
# Function to setup environment file
setup_environment() {
    echo "Setting up environment configuration..." >> logs/node_env.log

    ENV_FILE="$PWD"/.env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS version
        sed -i '' "3s/.*/SMART_CONTRACT_ADDRESS=$SMART_CONTRACT_ADDRESS/" "$ENV_FILE"
    else
        # Linux version
        sed -i "3s/.*/SMART_CONTRACT_ADDRESS=$SMART_CONTRACT_ADDRESS/" "$ENV_FILE"
    fi

    echo "Environment file updated with SMART_CONTRACT_ADDRESS: $SMART_CONTRACT_ADDRESS" >> logs/node_env.log
}