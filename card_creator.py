import sys
import logging

sys.path.append('./external/anki/')

from anki import Collection as aopen


class CardCreator:
    def __init__(self, coll_file, deck_name):
        self.coll_file = coll_file
        self.deck_name = deck_name

    def create(self, card_front, card_back):
        logging.info("Get Collection/Deck '" + self.coll_file + "/" + self.deck_name +
              "'")
        deck = aopen(self.coll_file)
        deckId = deck.decks.id(self.deck_name)

        deck.decks.select(deckId)
        basic_model = deck.models.byName('Basic')
        basic_model['did'] = deckId
        deck.models.save(basic_model)
        deck.models.setCurrent(basic_model)

        # todo I don't see any other ways to prevent creating a new Deck
        if deck.cardCount == 0:
            sys.exit("ERROR: Collection/Deck '" + coll_file + "/" + deck_name +
                     "' does not exist.")

        logging.info("Deck has " + str(deck.cardCount()) + " cards")

        logging.info("Make a new Card for: " + card_front)
        fact = deck.newNote()
        fact['Front'] = card_front
        fact['Back'] = card_back

        # Add Card to the Deck
        try:
            deck.addNote(fact)
        except:
            if hasattr(e, "data"):
                sys.exit("ERROR: Could not add '" + e.data['field'] + "': " +
                         e.data['type'])
            else:
                sys.exit(e)

        # Done.
        logging.info("Save the Deck")
        deck.save()
        deck.close()
