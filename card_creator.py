import json
import logging
import urllib.request


class CardCreator:
    def __init__(self, deck_name):
        self.deck_name = deck_name

    def request(self, action, **params):
        return {'action': action, 'params': params, 'version': 6}

    def invoke(self, action, **params):
        requestJson = json.dumps(self.request(
            action, **params)).encode('utf-8')
        response = json.load(urllib.request.urlopen(
            urllib.request.Request('http://localhost:8765', requestJson)))
        if len(response) != 2:
            raise Exception('response has an unexpected number of fields')
        if 'error' not in response:
            raise Exception('response is missing required error field')
        if 'result' not in response:
            raise Exception('response is missing required result field')
        if response['error'] is not None:
            raise Exception(response['error'])
        return response['result']

    def create(self, card_front, card_back):
        logging.info("Adding note to " + self.deck_name)
        self.invoke('addNote',
                    note={
                        "deckName": self.deck_name,
                        "modelName": "Basic",
                        "fields": {
                            "Front": card_front,
                            "Back": card_back,
                        },
                    })

        logging.info("Note added.")
