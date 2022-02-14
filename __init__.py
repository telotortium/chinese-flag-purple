#!/usr/bin/env python3
# Chinese Purple Flag
# Anki 2 addon
# Author telotortium
# https://telotortium.github.io/
#
# Finds duplicate audio notes, and marks them, suspending the duplicates with
# a purple flag (hence the name).

import aqt
import re
import sys

from aqt import mw
from aqt.qt import *

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# define a Handler which writes DEBUG messages or higher to sys.stdout (console
# output when Anki is run from a console).
console = logging.StreamHandler(stream=sys.stdout)
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logger.addHandler(console)

# define a Handler which writes INFO messages or higher to sys.stderr
# (debug console in Anki GUI)
console = logging.StreamHandler(stream=sys.stderr)
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logger.addHandler(console)

logger.debug("chinese-flag-purple loaded")

EXTRACT_CHINESE_RE = re.compile(r'^(.*?)<br/?><br/?>.*')
REMOVE_TONE_SPAN_RE = re.compile(r'<span class="tone\d">(.*?)</span>')
REMOVE_RUBY_RE = re.compile(r'<ruby>(.*?)<rt>.*?</rt></ruby>')

def extract_chinese_from_example(example):
    example = EXTRACT_CHINESE_RE.sub(r'\1', example)
    example = REMOVE_TONE_SPAN_RE.sub(r'\1', example)
    example = REMOVE_RUBY_RE.sub(r'\1', example)
    return example

def process_cards():
    logger.debug("entering process_cards")
    col = mw.window().col
    conf = {
        "Example 1": {
            "query": r'''"note:Chinese (advanced)\_" "example 1:_*"''',
            "tag_prefix": "duplicate-audio::example1::",
            "card_name": "Listening Example 1",
            "audio_field": "Example 1 Audio",
        },
        "Example 2": {
            "query": r'''"note:Chinese (advanced)\_" "example 2:_*"''',
            "tag_prefix": "duplicate-audio::example2::",
            "card_name": "Listening Example 2",
            "audio_field": "Example 2 Audio",
        },
        "Example 3": {
            "query": r'''"note:Chinese (advanced)\_" "example 3:_*"''',
            "tag_prefix": "duplicate-audio::example3::",
            "card_name": "Listening Example 3",
            "audio_field": "Example 3 Audio",
        },
        "中文": {
            "query": r'''"note:Chinese Grammar Wiki" 中文:_*''',
            "tag_prefix": "duplicate-audio::chinese-grammar-wiki::",
            "card_name": "Listening Translation",
            "audio_field": "中文 audio",
        },
        "Hanzi": {
            "query": r'''note:SpoonFedNote Hanzi:_*''',
            "tag_prefix": "duplicate-audio::spoon-fed-chinese::",
            "card_name": "Listening",
            "audio_field": "Audio",
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
            remaining_fields = fields[fields.index(field):]
            logger.debug(f"Processing {text} in notes {notes}")
            # Reverse remaining fields
            remaining_fields_rev = remaining_fields[::-1]
            for f, d in zip(remaining_fields_rev, [conf[f_]['chinese_to_notes'] for f_ in remaining_fields_rev]):
                if text in d:
                    canonical_nid = d[text][0]
                    if field != f and not (len(notes) == 1 and notes[0] == canonical_nid):
                        logger.debug(f"Field {field} {text} on notes {notes} has duplicate in field {f} on {canonical_nid}")
                    canonical_note = col.get_note(canonical_nid)
                    canonical_audio_field = conf[f]['audio_field']
                    canonical_audio = canonical_note[canonical_audio_field]
                    for nid in notes:
                        if nid == canonical_nid:
                            continue
                        note = col.get_note(nid)
                        tag_prefix = conf[field]['tag_prefix']
                        has_tag = False
                        for tag in note.tags:
                            if tag.startswith(tag_prefix):
                                has_tag = True
                                break
                        if not has_tag:
                            tag = f"{tag_prefix}{canonical_nid}"
                            logging.info(f'Adding tag {tag} to nid:{nid}')
                            note.add_tag(tag)
                            logging.info(f'Now tags are {note.string_tags()}')
                        # Add audio even to notes corresponding to duplicate
                        # cards, so that all notes with a given text share the
                        # same audio file.
                        audio_field = conf[field]['audio_field']
                        if canonical_audio and not note[audio_field]:
                            logging.info(f"Copying audio {canonical_audio} from field {canonical_audio_field} on {canonical_nid} "
                                             "to {audio_field} on note {nid}")
                            note[audio_field] = canonical_audio
                        # Tags and audio must be saved to collection for
                        # following search to work correctly
                        col.update_note(note)
                        cards = col.find_cards(f'''nid:{nid} "card:{conf[field]['card_name']}" -(is:suspended flag:7)''')
                        if len(cards) > 0:
                            logger.info(f'Suspending and purple flagging Card ids {cards}')
                            col.sched.suspend_cards(cards)
                            col.set_user_flag_for_cards(7, cards)  # 7 = purple
                            col.update_cards(col.get_card(c) for c in cards)
    logger.info("Chinese Purple Flag tool complete")



def fix_tags():
    logger.debug("entering fix_tags")
    col = mw.window().col
    all_tags = col.tags.all()
    logger.info(f'All tags: {all_tags}')
    for tag in all_tags:
        if tag.startswith('duplicate-audio__'):
            logger.info(f'Removing tag {tag}')
            col.tags.remove(tag)
        if re.match(r'^duplicate-audio:[^:].*', tag):
            new_tag = re.sub(r':', '::', tag)
            logger.info(f'Renaming tag {tag} to {new_tag}')
            col.tags.rename(tag, new_tag)
    logger.info("Chinese Purple Flag Fix tags tool complete")


def createMenu():
    a = QAction("Chinese Purple Flag", mw)
    a.triggered.connect(process_cards)
    mw.form.menuTools.addAction(a)

    a = QAction("Chinese Purple Flag Fix tags", mw)
    a.triggered.connect(fix_tags)
    mw.form.menuTools.addAction(a)

    def browserMenusInit(browser: aqt.browser.Browser):
        menu = QMenu("Chinese Purple Flag", browser.form.menubar)
        browser.form.menubar.addMenu(menu)

        a = QAction("Chinese Purple Flag", browser)
        a.triggered.connect(process_cards)
        menu.addAction(a)

        a = QAction("Chinese Purple Flag Fix tags", browser)
        a.triggered.connect(fix_tags)
        menu.addAction(a)

    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browserMenusInit)

createMenu()
