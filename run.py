import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from subprocess import Popen
from typing import Dict, Optional
from importlib.metadata import version
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import (
    Progress,
    TimeElapsedColumn,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

import psutil
import readchar


from daemon import PROCESSES, cleanup_processes, start_log_watcher

TOTAL_TIME_PLAYED = 0
EPISODES_PLAYED = 0
CONSOLE = Console()
LOG_COLOR = "dim"
HEADER_COLOR = "bold blue"
INFO_COLOR = "cyan"
ERROR_COLOR = "bold red"
WARNING_COLOR = "yellow"
SUCCESS_COLOR = "green"
DELINEATOR_COLOR = "bold white"
GENSYN_COLOR = "bold magenta"


def get_version() -> str:
    cmd = "./blockassist-venv/bin/python scripts/get_version.py"
    process = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        CONSOLE.print(
            f"Error getting version: {stderr.decode().strip()}", style=ERROR_COLOR
        )
        return "unknown"
    return stdout.decode().strip()


def create_logs_dir(clear_existing=True):
    if os.path.exists("logs") and clear_existing:
        CONSOLE.print("Clearing existing logs directory", style=LOG_COLOR)
        cmd = "rm -rf logs"
        process = Popen(cmd, shell=True)
        ret = process.wait()
        if ret != 0:
            sys.exit(ret)

    CONSOLE.print("Creating logs directory", style=LOG_COLOR)
    cmd = "mkdir -p logs"
    process = Popen(cmd, shell=True)
    ret = process.wait()
    if ret != 0:
        sys.exit(ret)


def create_evaluate_dir():
    if not os.path.exists("data/base_checkpoint/evaluate"):
        CONSOLE.print("Creating evaluate directory", style=LOG_COLOR)
        cmd = "mkdir -p data/base_checkpoint/evaluate"
        process = Popen(cmd, shell=True)
        ret = process.wait()
        if ret != 0:
            sys.exit(ret)
    else:
        CONSOLE.print("Evaluate directory already exists", style=LOG_COLOR)


def setup_venv():
    logging.info("Running setup_venv")
    cmd = "./scripts/venv_setup.sh | tee logs/venv.log"
    process = Popen(cmd, shell=True)
    ret = process.wait()
    if ret != 0:
        sys.exit(ret)


def setup_gradle():
    logging.info("Running setup_gradle")
    cmd = "./scripts/gradle_setup.sh"
    process = Popen(cmd, shell=True)
    PROCESSES.append(process)
    ret = process.wait()
    if ret != 0:
        sys.exit(ret)


def setup_yarn():
    logging.info("Running setup_yarn")
    cmd = "./scripts/yarn_setup.sh"
    process = Popen(cmd, shell=True)
    PROCESSES.append(process)
    ret = process.wait()
    if ret != 0:
        sys.exit(ret)


def run_malmo():
    logging.info("Running run_malmo")
    cmd = "./scripts/run_malmo.sh"
    process = Popen(cmd, shell=True)
    PROCESSES.append(process)
    return process


def run_yarn():
    logging.info("Running run_yarn")
    cmd = "./scripts/yarn_run.sh"
    process = Popen(cmd, shell=True)
    PROCESSES.append(process)
    return process


def run_open():
    logging.info("Running run_open")
    cmd = "open http://localhost:3000 2> /dev/null"
    process = Popen(cmd, shell=True)
    PROCESSES.append(process)
    return process


def run_blockassist(env: Optional[Dict] = None):
    logging.info("Running run_blockassist")
    cmd = "./scripts/run_blockassist.sh"
    process = Popen(cmd, shell=True, env=env)
    PROCESSES.append(process)
    return process


_ENTER_KEYS = ("\r", "\n")


def wait_for_enter(on_received=None):
    wait_for_keys(keys=_ENTER_KEYS, on_received=on_received)


def wait_for_keys(keys=_ENTER_KEYS, on_received=None):
    while True:
        char = readchar.readchar()
        if char in keys:  # Enter key
            if on_received:
                on_received(char)
            break
        else:
            CONSOLE.print(
                f"Unknown key pressed: {repr(char)}. Please press a valid key in ({keys}) to continue.",
                style=WARNING_COLOR,
            )


def send_blockassist_sigint(pid: int):
    logging.info("Running send_blockassist_sigint")
    CONSOLE.print(
        f"Sending SIGINT to BlockAssist process with PID: {pid}", style=LOG_COLOR
    )

    parent_process = psutil.Process(pid)
    if parent_process.is_running():
        logging.info(
            f"Parent process {pid} is running, attempting to send SIGINT to its children."
        )

    # Get all child processes of the parent process
    children = parent_process.children(recursive=True)
    if not children:
        logging.info(f"No child processes found for PID {pid}.")
        return

    logging.info(
        f"Found {len(children)} child processes for PID {pid}. Sending SIGINT to them."
    )
    for child in children:
        logging.info(f"Got child process '{child.name()}' with pid {child.pid}")

        if child.name() == "python3.10" or child.name() == "python":
            child.send_signal(signal.SIGINT)
            logging.info(f"Sent SIGINT to child process {child.pid} ('{child.name()}')")
        else:
            logging.info(f"Child process '{child.name()}' was not targeted")


def train_blockassist(env: Optional[Dict] = None):
    logging.info("Running train_blockassist")
    cmd = "./scripts/train_blockassist.sh"
    process = Popen(cmd, shell=True, env=env)
    PROCESSES.append(process)
    return process


def wait_for_login():
    logging.info("Running wait_for_login")
    # Extract environment variables from userData.json
    CONSOLE.print("Waiting for modal userData.json to be created...", style=INFO_COLOR)
    user_data_path = "modal-login/temp-data/userData.json"
    user_api_key_path = "modal-login/temp-data/userApiKey.json"
    while not os.path.exists(user_data_path):
        time.sleep(1)
    CONSOLE.print("Found userData.json. Proceeding...", style=SUCCESS_COLOR)

    # Read and parse the JSON file
    while True:
        try:
            with open(user_data_path, "r") as f:
                user_data = json.load(f)

            with open(user_api_key_path, "r") as f:
                user_api_key = json.load(f)

            d = os.environ.copy()

            for k in user_data.keys():
                d["BA_ORG_ID"] = user_data[k]["orgId"]
                d["BA_ADDRESS_EOA"] = user_data[k]["address"]
                d["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

            for k in user_api_key.keys():
                # Get the latest key
                d["BA_ADDRESS_ACCOUNT"] = user_api_key[k][-1]["accountAddress"]
                return d
        except Exception as e:
            CONSOLE.print("Waiting...", style=INFO_COLOR)
            time.sleep(1)


def run():
    global TOTAL_TIME_PLAYED
    global EPISODES_PLAYED
    CONSOLE.print("Creating directories...", style=LOG_COLOR)
    create_logs_dir(clear_existing=True)
    create_evaluate_dir()

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        filename="logs/run.log",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info("Running BlockAssist run.py script")
    CONSOLE.print(
        """
██████╗ ██╗      ██████╗  ██████╗██╗  ██╗
██╔══██╗██║     ██╔═══██╗██╔════╝██║ ██╔╝
██████╔╝██║     ██║   ██║██║     █████╔╝
██╔══██╗██║     ██║   ██║██║     ██╔═██╗
██████╔╝███████╗╚██████╔╝╚██████╗██║  ██╗
╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝

 █████╗ ███████╗███████╗██╗███████╗████████╗
██╔══██╗██╔════╝██╔════╝██║██╔════╝╚══██╔══╝
███████║███████╗███████╗██║███████╗   ██║
██╔══██║╚════██║╚════██║██║╚════██║   ██║
██║  ██║███████║███████║██║███████║   ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚══════╝   ╚═╝

By Gensyn""",
        style=GENSYN_COLOR,
    )

    if os.environ.get("HF_TOKEN") is None:
        logging.info("HF_TOKEN not found, prompting")
        CONSOLE.print(
            "Please enter your Hugging Face user access token and press ENTER. If you do not have a token, please refer to",
            style=INFO_COLOR,
        )
        CONSOLE.print()
        CONSOLE.print(
            "\n    https://huggingface.co/docs/hub/en/security-tokens", style=INFO_COLOR
        )
        CONSOLE.print()
        CONSOLE.print("for instructions on how to obtain one.", style=INFO_COLOR)

        while True:
            hf_token = input("Hugging Face token: ").strip()
            if hf_token:
                break

        os.environ["HF_TOKEN"] = hf_token
        CONSOLE.print("✅ HF_TOKEN set successfully", style=SUCCESS_COLOR)

    CONSOLE.print("Setting up virtualenv...", style=LOG_COLOR)
    setup_venv()

    CONSOLE.print(f"BlockAssist version: {get_version()}", style=GENSYN_COLOR)

    CONSOLE.print("Setting up Gradle...", style=LOG_COLOR)
    setup_gradle()

    CONSOLE.print("Compiling Yarn...", style=LOG_COLOR)
    setup_yarn()

    CONSOLE.print("Setting up Minecraft...", style=LOG_COLOR)
    start_log_watcher()
    proc_malmo = run_malmo()

    CONSOLE.print(Markdown("# LOGIN"), style=HEADER_COLOR)
    if sys.platform == "darwin":
        CONSOLE.print(
            "You will likely be asked to approve accessibility permissions. Please do so and, if necessary, restart the program.",
            style=WARNING_COLOR,
        )
    proc_yarn = run_yarn()
    time.sleep(5)
    if not os.path.exists("modal-login/temp-data/userData.json"):
        CONSOLE.print(
            "Running Gensyn Testnet login. If browser does not open automatically, please open a browser and go to http://localhost:3000 and click 'login' to continue.",
            style=INFO_COLOR,
        )
        CONSOLE.print(
            "Note, if it's your first time playing, also click 'log in')",
            style=INFO_COLOR,
        )
        run_open()

    env = wait_for_login()

    CONSOLE.print(Markdown("# START MINECRAFT"), style=HEADER_COLOR)
    CONSOLE.print(
        "Please press ENTER when two Minecraft windows have opened. This may take up to 5 minutes to happen.",
        style=INFO_COLOR,
    )
    CONSOLE.print(
        "NOTE: If one or both of the windows closes, please restart the program. You can also `tail -f logs/malmo.log` in another terminal if you suspect an error",
        style=WARNING_COLOR,
    )
    wait_for_enter()
    CONSOLE.print("Enter received", style=SUCCESS_COLOR)

    CONSOLE.print(Markdown("# INSTRUCTIONS"), style=HEADER_COLOR)
    time.sleep(1)
    CONSOLE.print(
        "The goal of the game is to build the structure in front of you.",
        style=INFO_COLOR,
    )
    CONSOLE.print("You do this by placing or destroying blocks.", style=INFO_COLOR)
    CONSOLE.print("Each building you build is a separate 'episode'", style=INFO_COLOR)
    CONSOLE.print("An AI player will assist you.", style=INFO_COLOR)
    CONSOLE.print("The more you play, the more the AI player learns.", style=INFO_COLOR)
    CONSOLE.print(
        "You should break red blocks and place blocks where indicated", style=INFO_COLOR
    )
    CONSOLE.print(
        "Click on the window and press ENTER to start playing", style=INFO_COLOR
    )
    CONSOLE.print(
        "Left click to break blocks, right click to place blocks", style=INFO_COLOR
    )
    CONSOLE.print(
        "Select an axe to break things, or various blocks, by pressing the number keys 1-9",
        style=INFO_COLOR,
    )
    CONSOLE.print("Use the WASD keys to move around", style=INFO_COLOR)
    CONSOLE.print(
        "Once you've finished playing, press ESC, then click back on the terminal window",
        style=INFO_COLOR,
    )

    proc_blockassist = run_blockassist(env=env)

    # TODO: Avoid duplicating the blockassist.globals._MAX_EPISODE_COUNT value
    # And find a more elegant way to pull it from the environment.
    _MAX_EPISODE_COUNT = 1

    for i in range(_MAX_EPISODE_COUNT):
        # Start timer in a separate thread
        CONSOLE.print(Markdown(f"\n## STARTING EPISODE {i}"), style=HEADER_COLOR)
        timer_running = True
        start_time = time.time()

        CONSOLE.print(
            f"\n[{i}] Please wait for the mission to load up on your Minecraft window. Press ENTER when you have finished recording your episode. **You may have to press it multiple times**",
            style=INFO_COLOR,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Recording episode"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=CONSOLE,
        ) as progress:
            task = progress.add_task("Recording episode", total=None)

            wait_for_enter()
            progress.stop()

        CONSOLE.print(f"\n[{i}] Enter received", style=SUCCESS_COLOR)

        CONSOLE.print(f"\n[{i}] Stopping episode recording", style=INFO_COLOR)
        send_blockassist_sigint(proc_blockassist.pid)
        TOTAL_TIME_PLAYED += int(time.time() - start_time)
        EPISODES_PLAYED += 1

    CONSOLE.print("Stopping Malmo", style=INFO_COLOR)
    proc_malmo.kill()
    proc_malmo.wait()

    CONSOLE.print(
        "Waiting for BlockAssist to stop - this might take a few minutes",
        style=INFO_COLOR,
    )
    proc_blockassist.wait()

    CONSOLE.print(Markdown("# MODEL TRAINING"), style=HEADER_COLOR)
    CONSOLE.print(
        "Your assistant is now training on the gameplay you recorded.", style=INFO_COLOR
    )
    CONSOLE.print(
        "This may take a while, depending on your hardware. Please keep this window open until you see 'Training complete'.",
        style=INFO_COLOR,
    )
    CONSOLE.print("Running training", style=INFO_COLOR)
    proc_train = train_blockassist(env=env)
    proc_train.wait()

    CONSOLE.print("Training complete", style=SUCCESS_COLOR)

    CONSOLE.print(
        Markdown("# UPLOAD TO HUGGINGFACE AND SMART CONTRACT"), style=HEADER_COLOR
    )
    # Monitor blockassist-train.log for HuggingFace upload confirmation and transaction hash
    CONSOLE.print(
        "Checking for upload confirmation and transaction hash...", style=LOG_COLOR
    )
    train_log_path = "logs/blockassist-train.log"
    upload_confirmed = False
    transaction_hash = None
    hf_path = None
    hf_size = None

    # Wait up to 30 seconds for the logs to appear
    for attempt in range(30):
        time.sleep(1)

        try:
            # Check blockassist-train.log for both logs
            if os.path.exists(train_log_path):
                with open(train_log_path, "r") as f:
                    lines = f.readlines()
                    last_15_lines = lines[-15:] if len(lines) >= 15 else lines

                for line in last_15_lines:
                    line = line.strip()
                    if (
                        "Successfully uploaded model to HuggingFace:" in line
                        and not upload_confirmed
                    ):
                        line_elems = line.split(
                            "Successfully uploaded model to HuggingFace: "
                        )[1].split(" ")
                        hf_path = line_elems[0].strip()
                        hf_size = line_elems[3].strip() + " " + line_elems[4].strip()
                        CONSOLE.print("✅ " + line, style=SUCCESS_COLOR)
                        upload_confirmed = True
                    elif "HF Upload API response:" in line and not transaction_hash:
                        CONSOLE.print("🔗 " + line, style=WARNING_COLOR)
                        transaction_hash = line

            # If we found both, we can stop monitoring
            if upload_confirmed and transaction_hash:
                CONSOLE.print(
                    "Copy your HuggingFace model path (e.g. 'block-fielding/bellowing_pouncing_horse_1753796381') and check for it here:\nhttps://gensyn-testnet.explorer.alchemy.com/address/0xE2070109A0C1e8561274E59F024301a19581d45c?tab=logs",
                    style=INFO_COLOR,
                )
                break

        except Exception as e:
            CONSOLE.print(f"Error reading log file: {e}", style=ERROR_COLOR)
            break

    # If we didn't find the logs after 30 seconds
    if not upload_confirmed and not transaction_hash:
        CONSOLE.print(
            "⚠️ No upload confirmation or transaction hash found in blockassist-train.log",
            style=ERROR_COLOR,
        )
    elif not upload_confirmed:
        CONSOLE.print(
            "⚠️ No HuggingFace upload confirmation found in blockassist-train.log",
            style=ERROR_COLOR,
        )
    elif not transaction_hash:
        CONSOLE.print(
            "⚠️ No transaction hash found in blockassist-train.log", style=ERROR_COLOR
        )

    CONSOLE.print(Markdown("# SHUTTING DOWN"), style=HEADER_COLOR)
    CONSOLE.print("Stopping Yarn", style=LOG_COLOR)
    proc_yarn.kill()

    CONSOLE.print(
        Markdown(f"# 🎉 SUCCESS! Your BlockAssist session has completed successfully!"),
        style=SUCCESS_COLOR,
    )
    CONSOLE.print(f"")
    CONSOLE.print(f"- Your gameplay was recorded and analyzed", style=INFO_COLOR)
    CONSOLE.print(
        f"- An AI model was trained on your building patterns", style=INFO_COLOR
    )
    CONSOLE.print(
        f"- The model was successfully uploaded to Hugging Face", style=INFO_COLOR
    )
    CONSOLE.print(f"- Your work helps train better AI assistants ", style=INFO_COLOR)
    CONSOLE.print(f"")
    CONSOLE.print(f"Stats:", style=INFO_COLOR)
    CONSOLE.print(f"")
    CONSOLE.print(f"- Episodes recorded: {EPISODES_PLAYED}", style=INFO_COLOR)
    CONSOLE.print(
        f"- Total gameplay time: {TOTAL_TIME_PLAYED // 60}m {TOTAL_TIME_PLAYED % 60}s",
        style=INFO_COLOR,
    )
    CONSOLE.print(f"- Model trained and uploaded: {hf_path}", style=INFO_COLOR)
    CONSOLE.print(f"- Model size: {hf_size}", style=INFO_COLOR)
    CONSOLE.print(f"")
    CONSOLE.print(f"🚀What to do next:", style=INFO_COLOR)
    CONSOLE.print(f"")
    CONSOLE.print(f"")
    CONSOLE.print(
        f"- Run BlockAssist again to improve your performance (higher completion %, faster time).",
        style=INFO_COLOR,
    )
    CONSOLE.print(
        f"- Check your model on Hugging Face: https://huggingface.co/{hf_path}",
        style=INFO_COLOR,
    )
    CONSOLE.print(
        f"- Screenshot your stats, record your gameplay, and share with the community on X (https://x.com/gensynai) or Discord (https://discord.gg/gensyn)",
        style=INFO_COLOR,
    )
    CONSOLE.print(f"")
    CONSOLE.print(f"Thank you for contributing to BlockAssist!", style=INFO_COLOR)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_processes()
