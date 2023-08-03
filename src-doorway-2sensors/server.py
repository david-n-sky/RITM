import log
import config
import requests
import uuid
import datetime
import json

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


class Server:
    def strToUuid(self, uid):
        return str(uuid.uuid3(uuid.NAMESPACE_X500, uid.upper()))

    def sendReport(self, direction, tags):
        body = {
            "updated_at": datetime.datetime.now().strftime(TIMESTAMP_FORMAT),
            "module": config.data['Server']['Module'],
            "entry": direction == "entry",
        }

        if tags is not None:
            uuids = []
            for tag in tags:
                uuids.append(self.strToUuid(tag))
            body['items'] = uuids

        url = config.data['Server']['Url']
        headers = {'Content-type': 'application/json', "accept": "application/json"}

        log.debug(f"Sending report: {json.dumps(body)}")
        resp = requests.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            log.info(f"Failed to send the report, http status code is {resp.status_code}")
            return

        log.info(f"Report sent")
