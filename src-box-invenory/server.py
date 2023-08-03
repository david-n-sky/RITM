import log
import config
import requests
import uuid
import datetime
import json

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


class Server:
    def changeUuidDb(self, uuid):
        try:
            url = config.data['Server']['AuthUrl']
            headers = {'Content-type': 'application/json', "accept": "application/json"}
            body = {'user': uuid, 'module': config.data_uuid['Server']['Module']}
            resp = requests.post(url, json=body, headers=headers)
            log.debug(f"auth uuid={uuid} => http status={resp.status_code}")

            if resp.status_code == 200 or resp.status_code == 504:  # 200 - все хорошо, 504 - Gateway Time Out
                if str(uuid) in self.get_uuids():
                    log.info(f"Карта {uuid} уже есть")
                else:
                    with open("db", "a") as db:
                        db.write(f'{uuid}\n')
                    log.info(f"Карта {uuid} добавлена")

            elif resp.status_code == 403:
                with open("db", "r+") as db:
                    x = db.read()
                with open("db", "w") as db:
                    x = x.replace(f"{uuid}\n", "")
                    db.write(x)
                    del x
                print(f"Карта {uuid} удалена")

        except Exception as e:
            log.debug(f"auth uuid={uuid} => error: {e}")

    def strToUuid(self, uid):
        return str(uuid.uuid3(uuid.NAMESPACE_X500, uid.upper()))

    def get_uuids(self):
        with open("db", "r+") as db:
            allowed_uuids = db.read().splitlines()
        return allowed_uuids

    def isUidAllowed(self, uid):
        return self.changeUuidDb(self.strToUuid(uid))

    def sendInventory(self, user, tags):
        log.info('sending inventory..')
        body = {
            "updated_at": datetime.datetime.now().strftime(TIMESTAMP_FORMAT),
            'module': config.data_uuid['Server']['Module']
        }

        if user is None:
            body['user'] = None
        else:
            body['user'] = user

        if tags is not None:
            uuids = []
            for tag in tags:
                uuids.append(self.strToUuid(tag))
            body['items'] = uuids

        url = config.data['Server']['InventoryUrl']
        headers = {'Content-type': 'application/json', "accept": "application/json"}

        log.debug(f"Sending inventory update: {json.dumps(body)}")
        try:
            resp = requests.post(url, json=body, headers=headers)

            if resp.status_code == 200:
                log.info(f"Inventory update sent: {body}")

        except Exception as e:
            log.error(f"Failed to send inventory update, error: {e}")
