import requests
from resonance.utils.update.base_update_utils import BaseUpdateUtils, LatestInfoResponse
from version import __version__

RES_ID = "RS-Autopilot"
LATEST_URL = f"https://mirrorchyan.com/api/resources/{RES_ID}/latest"


class MirrorUpdateUtils(BaseUpdateUtils):
    def get_latest_info(self, cdk: str):
        query = {"current_version": __version__, "cdk": cdk, "user_agent": RES_ID}
        response = requests.get(LATEST_URL, params=query)
        self.data = LatestInfoResponse.model_validate(response.json())
        return self.data
