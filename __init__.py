#!/usr/bin/env python3
# Chinese Purple Flag
# Anki 2 addon
# Author telotortium
# https://telotortium.github.io/
#
# Finds duplicate audio notes, and marks them, suspending the duplicates with
# a purple flag (hence the name).

from aqt import mw
from aqt.qt import *
import re
import sys

import logging
logger = logging.getLogger("chinese_purple_flag")
logger.setLevel(logging.DEBUG)
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logger.addHandler(console)

EXTRACT_CHINESE_RE = re.compile(r'^(.*?)<br/?><br/?>.*')
REMOVE_TONE_SPAN_RE = re.compile(r'<span class="tone\d">(.*?)</span>')
REMOVE_RUBY_RE = re.compile(r'<ruby>(.*?)<rt>.*?</rt></ruby>')

def extract_chinese_from_example(example):
    example = EXTRACT_CHINESE_RE.sub(r'\1', example)
    example = REMOVE_TONE_SPAN_RE.sub(r'\1', example)
    example = REMOVE_RUBY_RE.sub(r'\1', example)
    return example

def process_cards():
    col = mw.window().col
    conf = {
        "Example 1": {
            "query": r'''"note:Chinese (advanced)\_" "example 1:_*"''',
            "tag_prefix": "duplicate-audio::example1::",
            "card_name": "Listening Example 1",
        },
        "Example 2": {
            "query": r'''"note:Chinese (advanced)\_" "example 2:_*"''',
            "tag_prefix": "duplicate-audio::example2::",
            "card_name": "Listening Example 2",
        },
        "Example 3": {
            "query": r'''"note:Chinese (advanced)\_" "example 3:_*"''',
            "tag_prefix": "duplicate-audio::example3::",
            "card_name": "Listening Example 3",
        },
        "中文": {
            "query": r'''"note:Chinese Grammar Wiki" 中文:_*''',
            "tag_prefix": "duplicate-audio::chinese-grammar-wiki::",
            "card_name": "Listening Translation",
        },
        "Hanzi": {
            "query": r'''note:SpoonFedNote Hanzi:_*''',
            "tag_prefix": "duplicate-audio::spoon-fed-chinese::",
            "card_name": "Listening",
        },
    }
    for field in conf.keys():
        conf[field]['notes'] = col.find_notes(conf[field]['query'])
        conf[field]['chinese_to_notes'] = dict()
        for nid in conf[field]['notes']:
            note = col.get_note(nid)
            text = extract_chinese_from_example(note[field])
            d = conf[field]['chinese_to_notes']
            nids = d.get(text, [])
            nids.append(nid)
            d[text] = nids

    fields = ["Example 1", "Example 2", "Example 3", "中文", "Hanzi"]
    for field in fields:
        for (text, notes) in conf[field]['chinese_to_notes'].items():
            remaining_fields = fields[fields.index(field)+1:]
            # Reverse remaining fields
            for d in [conf[f]['chinese_to_notes'] for f in remaining_fields][::-1]:
                if text in d:
                    canonical_nid = d[text][0]
                    logger.warn(f"Example 1 {text} on notes {notes} has duplicate in SpoonFedNote {canonical_nid}")
                    for nid in notes:
                        note = col.get_note(nid)
                        tag_prefix = conf[field]['tag_prefix']
                        has_tag = False
                        for tag in note.tags:
                            if tag.startswith(tag_prefix):
                                has_tag = True
                                break
                        if not has_tag:
                            tag = f"{tag_prefix}{canonical_nid}"
                            logging.warning(f'Adding tag {tag} to nid:{nid}')
                            note.add_tag(tag)
                            logging.warning(f'Now tags are {note.string_tags()}')
                        col.update_note(note)
                        cards = col.find_cards(f'''nid:{nid} "card:{conf[field]['card_name']}" -is:suspended''')
                        logger.warning(f'Suspending Card ids {cards}')
                        col.sched.suspend_cards(cards)
                        for cid in cards:
                            card = col.get_card(cid)
                            card.set_user_flag(7)  # purple
                            col.update_card(card)
    col.flush()



def fix_tags():
    col = mw.window().col
    all_tags = col.tags.all()
    logger.warning(f'All tags: {all_tags}')
    for tag in all_tags:
        if tag.startswith('duplicate-audio__'):
            logger.warning(f'Removing tag {tag}')
            col.tags.remove(tag)
        if re.match(r'^duplicate-audio:[^:].*', tag):
            new_tag = re.sub(r':', '::', tag)
            logger.warning(f'Renaming tag {tag} to {new_tag}')
            col.tags.rename(tag, new_tag)
    col.flush()


def createMenu():
    a = QAction("Chinese Purple Flag", mw)
    a.triggered.connect(process_cards)
    mw.form.menuTools.addAction(a)

    a = QAction("Chinese Purple Flag Fix tags", mw)
    a.triggered.connect(fix_tags)
    mw.form.menuTools.addAction(a)

createMenu()
