
from dataclasses import dataclass
from typing import Optional, List, Callable
import re

from anki.utils import htmlToTextLine
from aqt import mw, gui_hooks
from aqt.utils import showInfo

def _create_configuration_from_config():
  def inner(configuration_dict):
    whole_text_configurations = [
      WholeTextConfiguration(
        model_name=whole_text_configuration["noteType"],
        field_name_to_copy_from=whole_text_configuration["sourceField"],
        field_name_to_copy_to=whole_text_configuration["destinationField"],
        blank_out_word_after_copy=whole_text_configuration["blankOutWordAfterCopy"],
        copy_only_if_field_empty=whole_text_configuration["copyOnlyIfEmpty"],
        regex_remove=whole_text_configuration.get("textToRemoveRegex"),
        blank_out_text_regex=whole_text_configuration.get("blankOutTextRegex")
      )
      for whole_text_configuration in configuration_dict["wholeTextSearchConfigurations"]
    ]

    per_character_configurations = [
      PerCharacterConfiguration(
        model_name=per_character_configuration["noteType"],
        field_name_to_copy_from=per_character_configuration["sourceField"],
        field_names_to_copy_to=per_character_configuration["destinationFields"],
        copy_only_if_field_empty=per_character_configuration["copyOnlyIfEmpty"],
        filter_characters=filter_kanji if per_character_configuration["filterCharacters"] else None
      )
      for per_character_configuration in configuration_dict["perCharacterSearchConfigurations"]
    ]

    return SmartCopyConfiguration(
      subject_field_name=configuration_dict["subjectField"],
      whole_text_configurations=whole_text_configurations,
      per_character_configurations=per_character_configurations
    )

  config = mw.addonManager.getConfig(__name__)
  return inner(config)

@dataclass(frozen=True)
class PerCharacterConfiguration:
  # Name of the field in the reference note to copy from.
  field_name_to_copy_from: str

  # Name of the model of the reference note to copy from.
  model_name: str

  # List of fields to copy to. The index in the list corresponds to the index of the character in
  # the contents of the field `subject_field_name`.
  field_names_to_copy_to: List[str]

  # `True` if the copy should occur only when the field is not empty, `False` in case the copy
  # should anyway occur.
  copy_only_if_field_empty: bool

  # Function that returns `True` if the character should be searched for and `False` otherwise.
  filter_characters: Callable[[str], bool] = lambda character: True

@dataclass(frozen=True)
class WholeTextConfiguration:
  # Name of the field in the reference note to copy from.
  field_name_to_copy_from: str

  # Name of the field in the new note to copy to.
  field_name_to_copy_to: str

  # Name of the model of the reference note to copy from.
  model_name: str

  # `True` if the contents of the field `subject_field_name` that appears in the contents of the
  # field `field_name_to_copy_from` should be blanked out after copying, `False` otherwise.
  #
  # Example:
  # - The contents of `source_file_name` = "foo"
  # - The contents of `field_name_to_copy_from` = "foobar"
  # The result would be: `___bar`.
  blank_out_word_after_copy: bool

  # `True` if the copy should occur only when the field is not empty, `False` in case the copy
  # should anyway occur.
  copy_only_if_field_empty: bool

  # All substrings in the contents of the field `field_name_to_copy_from` that match `regex_remove`
  # will be removed when copied to `field_name_to_copy_to`.
  regex_remove: Optional[str] = None

  # The contents of the field `field_name_to_copy_from` will be copied such that the first match to
  # the regex `blank_out_text_regex` will be blanked out. Has no effect if
  # `blank_out_word_after_copy` is `False` or this is `None`.
  #
  # Useful in case the word in `source_file_name` doesn't appear in its original form, but in some
  # conjugation.
  #
  # Example:
  # - The contents of `source_file_name` = "foo"
  # - The contents of `field_name_to_copy_from` = "<b>fooie</b>bar"
  # - `blank_out_text_regex` is equal to `r"<b>(.*?)</b>"`.
  # The result would be: `_____bar`.
  blank_out_text_regex: Optional[str] = None

def filter_kanji(character):
    '''
    Returns `True` if the character is Kanji, `False` otherwise.
    '''
    return ord(character) >= 19968 and ord(character) <= 40879

@dataclass(frozen=True)
class SmartCopyConfiguration:
  subject_field_name: str

  whole_text_configurations: List[WholeTextConfiguration]

  per_character_configurations: List[PerCharacterConfiguration]

FIELD_SEPARATOR = "\x1f"

def smart_copy(changed, note, current_field_index):
  configuration = _create_configuration_from_config()

  if not _model_is_correct_type(configuration, note.model()):
    return changed

  if note.keys()[current_field_index] != configuration.subject_field_name:
    return changed

  text_to_search = (
    htmlToTextLine(mw.col.media.strip(note[configuration.subject_field_name])).strip()
  )

  if not text_to_search:
    return changed

  note_ids = (
    mw.col.db.list("SELECT id FROM notes WHERE flds LIKE " +
                   f"'%{FIELD_SEPARATOR}{text_to_search}{FIELD_SEPARATOR}%'")
  )

  note_changed = False

  for whole_text_configuration in configuration.whole_text_configurations:
    source = whole_text_configuration.field_name_to_copy_from
    destination = whole_text_configuration.field_name_to_copy_to

    if destination not in note or \
        (note[destination] and whole_text_configuration.copy_only_if_field_empty):
      continue

    note_to_copy_from = (
      _get_note_from_note_id_with_model(note_ids, whole_text_configuration.model_name)
    )

    if note_to_copy_from is None or source not in note_to_copy_from:
      continue

    source_value = note_to_copy_from[source]

    if whole_text_configuration.regex_remove:
      source_value = re.sub(whole_text_configuration.regex_remove, "", source_value)

    source_value = (
      _source_value_after_blanking_out_word(source_value, whole_text_configuration, text_to_search)
    )

    if _source_exists_in_destination(source_value, note[destination]):
      continue

    if not note[destination]:
      note[destination] = source_value
    else:
      note[destination] += "<br>" + source_value

    note_changed = True

  for per_character_configuration in configuration.per_character_configurations:
    source = per_character_configuration.field_name_to_copy_from

    index_of_filtered_character = 0

    for character in text_to_search:
      if not per_character_configuration.filter_characters(character):
        continue

      if index_of_filtered_character >= len(per_character_configuration.field_names_to_copy_to):
        break

      destination = per_character_configuration.field_names_to_copy_to[index_of_filtered_character]
      index_of_filtered_character += 1

      if destination not in note or \
          (note[destination] and per_character_configuration.copy_only_if_field_empty):
        continue

      note_ids = (
        mw.col.db.list("SELECT id FROM notes WHERE flds LIKE " +
                       f"'%{FIELD_SEPARATOR}{character}{FIELD_SEPARATOR}%'")
      )

      note_to_copy_from = (
        _get_note_from_note_id_with_model(note_ids, per_character_configuration.model_name)
      )

      if note_to_copy_from is None or source not in note_to_copy_from:
        continue

      source_value = note_to_copy_from[source]

      if _source_exists_in_destination(source_value, note[destination]):
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

def _get_note_from_note_id_with_model(note_ids, model_name):
  for note_id in note_ids:
    note = mw.col.getNote(note_id)

    if note.model()["name"] == model_name:
      return note

  return None

def _source_value_after_blanking_out_word(source_value, whole_word_configuration, text_to_search):
  if not whole_word_configuration.blank_out_word_after_copy:
    return source_value

  if not whole_word_configuration.blank_out_text_regex:
    return re.sub(text_to_search, "_" * len(text_to_search), source_value)

  regex_to_search = ".*(" + whole_word_configuration.blank_out_text_regex + ").*"

  blank_out_match = re.match(regex_to_search, source_value)

  if not blank_out_match:
    return re.sub(text_to_search, "_" * len(text_to_search), source_value)

  text_to_blank_out = blank_out_match.group(2)
  source_text_to_be_replaced = blank_out_match.group(1)

  return re.sub(source_text_to_be_replaced, "_" * len(text_to_blank_out), source_value)

def _model_is_correct_type(configuration, model):
  '''
  Returns `True` if model has the subject field (The field with the text to search for), `False`
  otherwise.
  '''
  fields = mw.col.models.fieldNames(model)
  return configuration.subject_field_name in fields

def _source_exists_in_destination(source_value, destination_value):
  # For some reason, after focusing on a field, the image HTML tags in it turn from
  # `<img src="foo.jpg" />` to `<img src="foo.jpg">`. The solution to this is to remove `/` from the
  # `source_value` and see if the result appears in `destination_value`.
  source_value_without_backslash = re.sub(r" ?/>", ">", source_value)
  return source_value in destination_value or source_value_without_backslash in destination_value

gui_hooks.editor_did_unfocus_field.append(smart_copy)
