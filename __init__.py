
from dataclasses import dataclass
from typing import Optional
import re

from anki.utils import htmlToTextLine
from aqt import mw, gui_hooks
from aqt.utils import showInfo

source_field_name = "Word (in Kanji/Hanzi)"

# TODO: 1. Put image only if it's not empty (Maybe do it for others?).

@dataclass(frozen=True)
class SmartCopyDefinition:
  source_field_name: str
  destination_field_name: str
  blank_out_word_after_copy: bool
  add_only_if_not_empty: bool
  regex_remove: Optional[str] = None
  blank_out_word_indicator: Optional[str] = None

smart_copy_definitions = [
  SmartCopyDefinition(
    "sentence",
    "Counter Word, Personal Connection, Full Sentence, Extra Info (Back side)",
    False,
    False,
    r"\[.*?\]"
  ),
  SmartCopyDefinition("vocab-audio", "Pronunciation (Recording)", False, False),
  SmartCopyDefinition("sentence-audio", "Pronunciation (Recording)", False, False),
  SmartCopyDefinition("image", "Picture/Red Front Side", False, True),
  SmartCopyDefinition(
    "sentence",
    "Example Sentence w/ Blanked Out Word (optional)",
    True,
    False,
    r"\[.*?\]",
    r".*<b>(.*?)</b>.*"
  )
]

FIELD_SEPARATOR = "\x1f"

def smart_copy(changed, note, current_field_index):
  if not _model_is_correct_type(note.model()):
    return False

  if note.keys()[current_field_index] != source_field_name:
    return False

  text_to_search = htmlToTextLine(mw.col.media.strip(note[source_field_name])).strip()

  if not text_to_search:
    return False

  reference_cards = (
    mw.col.db.list("SELECT id FROM notes WHERE flds LIKE " +
                   f"'%{FIELD_SEPARATOR}{text_to_search}{FIELD_SEPARATOR}%'")
  )

  if not reference_cards:
    showInfo(f"No reference cards found.")
    return False

  note_to_copy_from = mw.col.getNote(reference_cards[0])

  for definition in smart_copy_definitions:
    source = definition.source_field_name
    destination = definition.destination_field_name

    if destination not in note:
      continue

    source_value = note_to_copy_from[source]

    if definition.regex_remove:
      source_value = re.sub(definition.regex_remove, "", source_value)

    source_value = _sentence_after_blanking_out_word(source_value, definition, text_to_search)

    if source_value not in note[destination]:
      if note[destination] and definition.add_only_if_not_empty:
        continue

      if not note[destination]:
        note[destination] = source_value
      else:
        note[destination] += "<br>" + source_value

  note.flush()

  return True

def _sentence_after_blanking_out_word(source_value, smart_copy_definition, text_to_search):
  if not smart_copy_definition.blank_out_word_after_copy:
    return source_value

  if not smart_copy_definition.blank_out_word_indicator:
    return re.sub(text_to_search, "_" * len(text_to_search), source_value)

  blank_out_match = re.match(smart_copy_definition.blank_out_word_indicator, source_value)

  if not blank_out_match:
    return re.sub(text_to_search, "_" * len(text_to_search), source_value)

  text_to_blank_out = blank_out_match.group(1)
  return re.sub(text_to_blank_out, "_" * len(text_to_blank_out), source_value)

def _model_is_correct_type(model):
    '''
    Returns `True` if model has both source field and destination field, `False` otherwise.
    '''
    fields = mw.col.models.fieldNames(model)

    destination_fields_names = (
      [definition.destination_field_name for definition in smart_copy_definitions]
    )

    return (source_field_name in fields and
      any(destination_field_name in fields
          for destination_field_name in destination_fields_names))

gui_hooks.editor_did_unfocus_field.append(smart_copy)
