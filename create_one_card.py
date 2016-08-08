#!/usr/bin/env python
'''
create_date_cards.py
A python script to create Anki cards with dates from American History.
'''
import card_creator
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--front', help='Card front')
parser.add_argument('--back', help='Card back')
parser.add_argument(
    '--collection', help='Path to anki collection file (.anki file)')
parser.add_argument('--deck', help='Anki deck name')
args = parser.parse_args()

card = card_creator.CardCreator(args.collection, args.deck)
card.create(args.front, args.back)
