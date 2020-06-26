
from dataclasses import dataclass
from typing import Optional
import re

from anki.utils import htmlToTextLine
from aqt import mw, gui_hooks
from aqt.utils import showInfo

source_field_name = "Word (in Kanji/Hanzi)"

@dataclass(frozen=True)
class SmartCopyDefinition:
  # Name of the field in the reference note to copy from.
  field_name_to_copy_from: str

  # Name of the field in the new note to copy to.
  field_name_to_copy_to: str

  # Name of the model of the reference note to copy from.
  model_name: str

  # `True` if the contents of the field `source_field_name` that appears in the contents of the
  # field `field_name_to_copy_from` should be blanked out after copying, `False` otherwise.
  #
  # Example:
  # - The contents of `source_file_name` = "foo"
  # - The contents of `field_name_to_copy_from` = "foobar"
  # The result would be: `___bar`.
  blank_out_word_after_copy: bool

  # `True` if the copy should occur only when the field is not empty, `False` in case the copy
  # should anyway occur.
  copy_only_if_field_not_empty: bool

  # All substrings in the contents of the field `field_name_to_copy_from` that match `regex_remove`
  # will be removed when copied to `field_name_to_copy_to`.
  regex_remove: Optional[str] = None

  # The contents of the field `field_name_to_copy_from` will be copied such that the first match to
  # the regex `blank_out_word_regex` will be blanked out. Has no effect if
  # `blank_out_word_after_copy` is `False` or this is `None`.
  #
  # Useful in case the word in `source_file_name` doesn't appear in its original form, but in some
  # conjugation.
  #
  # Example:
  # - The contents of `source_file_name` = "foo"
  # - The contents of `field_name_to_copy_from` = "<b>fooie</b>bar"
  # - `blank_out_word_regex` is equal to `r".*<b>(.*?)</b>.*"`.
  # The result would be: `_____bar`.
  blank_out_word_regex: Optional[str] = None

smart_copy_definitions = [
  SmartCopyDefinition(
    field_name_to_copy_from="sentence",
    field_name_to_copy_to="Counter Word, Personal Connection, Full Sentence, Extra Info (Back side)",
    model_name="Japanese v2-62274-e76b4",
    blank_out_word_after_copy=False,
    copy_only_if_field_not_empty=False,
    regex_remove=r"\[.*?\]"
  ),
  SmartCopyDefinition(
    field_name_to_copy_from="vocab-audio",
    field_name_to_copy_to="Pronunciation (Recording)",
    model_name="Japanese v2-62274-e76b4",
    blank_out_word_after_copy=False,
    copy_only_if_field_not_empty=False
  ),
  SmartCopyDefinition(
    field_name_to_copy_from="sentence-audio",
    field_name_to_copy_to="Pronunciation (Recording)",
    model_name="Japanese v2-62274-e76b4",
    blank_out_word_after_copy=False,
    copy_only_if_field_not_empty=False
  ),
  SmartCopyDefinition(
    field_name_to_copy_from="image",
    field_name_to_copy_to="Picture/Red Front Side",
    model_name="Japanese v2-62274-e76b4",
    blank_out_word_after_copy=False,
    copy_only_if_field_not_empty=True
  ),
  SmartCopyDefinition(
    field_name_to_copy_from="sentence",
    field_name_to_copy_to="Example Sentence w/ Blanked Out Word (optional)",
    model_name="Japanese v2-62274-e76b4",
    blank_out_word_after_copy=True,
    copy_only_if_field_not_empty=False,
    regex_remove=r"\[.*?\]",
    blank_out_word_regex=r".*<b>(.*?)</b>.*"
  )
]

FIELD_SEPARATOR = "\x1f"

def smart_copy(changed, note, current_field_index):
  if not _model_is_correct_type(note.model()):
    return changed

  if note.keys()[current_field_index] != source_field_name:
    return changed

  text_to_search = htmlToTextLine(mw.col.media.strip(note[source_field_name])).strip()

  if not text_to_search:
    return changed

  reference_cards = (
    mw.col.db.list("SELECT id FROM notes WHERE flds LIKE " +
                   f"'%{FIELD_SEPARATOR}{text_to_search}{FIELD_SEPARATOR}%'")
  )

  if not reference_cards:
    showInfo(f"No reference cards found.")
    return changed

  note_changed = False

  for definition in smart_copy_definitions:
    source = definition.field_name_to_copy_from
    destination = definition.field_name_to_copy_to

    note_to_copy_from = (
      _get_note_from_reference_card_with_model(reference_cards, definition.model_name)
    )

    if note_to_copy_from is None:
      continue

    if destination not in note or source not in note_to_copy_from:
      continue

    source_value = note_to_copy_from[source]

    if definition.regex_remove:
      source_value = re.sub(definition.regex_remove, "", source_value)

    source_value = _sentence_after_blanking_out_word(source_value, definition, text_to_search)

    if source_value not in note[destination]:
      if note[destination] and definition.copy_only_if_field_not_empty:
        continue

      if not note[destination]:
        note[destination] = source_value
      else:
        note[destination] += "<br>" + source_value

      note_changed = True

  if not note_changed:
    return changed

  note.flush()

  return True

def _get_note_from_reference_card_with_model(reference_cards, model_name):
  for reference_card in reference_cards:
    note = mw.col.getNote(reference_card)

    if note.model()["name"] == model_name:
      return note

  return None

def _sentence_after_blanking_out_word(source_value, smart_copy_definition, text_to_search):
  if not smart_copy_definition.blank_out_word_after_copy:
    return source_value

  if not smart_copy_definition.blank_out_word_regex:
    return re.sub(text_to_search, "_" * len(text_to_search), source_value)

  blank_out_match = re.match(smart_copy_definition.blank_out_word_regex, source_value)

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
      [definition.field_name_to_copy_to for definition in smart_copy_definitions]
    )

    return (source_field_name in fields and
      any(destination_field_name in fields
          for destination_field_name in destination_fields_names))

gui_hooks.editor_did_unfocus_field.append(smart_copy)
