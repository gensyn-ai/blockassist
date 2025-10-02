import logging

import requests

MODAL_PROXY_URL = "http://localhost:3000/api/"

logger = logging.getLogger(__name__)


class ModalSwarmCoordinator:
    def __init__(self, org_id: str) -> None:
        self.org_id = org_id

    def submit_hf_upload(
        self, training_id, hf_id, num_sessions, telemetry_enabled, git_ref
    ):
        try:
            send_via_api(
                self.org_id,
                "submit-hf-upload",
                {
                    "trainingId": training_id,
                    "huggingFaceId": hf_id,
                    "numSessions": num_sessions,
                    "telemetryEnabled": telemetry_enabled,
                    "gitRef": git_ref,
                },
            )
        except requests.exceptions.HTTPError as e:
            if e.response is None or e.response.status_code != 500:
                raise

            logger.debug("Unknown error calling submit-hf-upload endpoint! Continuing.")


def send_via_api(org_id, method, args):
    # Construct URL and payload.
    url = MODAL_PROXY_URL + method
    payload = {"orgId": org_id} | args

    # Send the POST request.
    response = requests.post(url, json=payload)
    response.raise_for_status()  # Raise an exception for HTTP errors
    logger.info("HF Upload API response: %s", response.json())
    return response.json()
