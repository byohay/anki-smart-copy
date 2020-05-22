
from anki.utils import htmlToTextLine
from aqt import mw, gui_hooks
from aqt.utils import showInfo

source_field_name = "Word (in Kanji/Hanzi)"

source_to_destination_fields = {
  "sentence": "Counter Word, Personal Connection, Full Sentence, Extra Info (Back side)",
  "sentence-audio": "Pronunciation (Recording)",
  "image": "Picture/Red Front Side"
}

FIELD_SEPARATOR = "\x1f"

def add_example_sentence(changed, note, current_field_index):
  if not _model_is_correct_type(note.model()):
    return False

  if note.keys()[current_field_index] != source_field_name:
    return False

  source_text = htmlToTextLine(mw.col.media.strip(note[source_field_name])).strip()

  reference_cards = (
    mw.col.db.list("SELECT id FROM notes WHERE flds LIKE " +
                   f"'%{FIELD_SEPARATOR}{source_text}{FIELD_SEPARATOR}%'")
  )

  if not reference_cards:
    showInfo(f"No reference cards found.")
    return False

  note_to_copy_from = mw.col.getNote(reference_cards[0])

  for source, destination in source_to_destination_fields.items():
    if note[destination] is None:
      continue

    source_value = note_to_copy_from[source]

    if source_value not in note[destination]:
      note[destination] += "<br><br>" + source_value

  note.flush()

  return True

def _model_is_correct_type(model):
    '''
    Returns `True` if model has both source field and destination field, `False` otherwise.
    '''
    fields = mw.col.models.fieldNames(model)

    return (source_field_name in fields and
      any(destination_field_name in fields
          for destination_field_name in source_to_destination_fields.values()))

gui_hooks.editor_did_unfocus_field.append(add_example_sentence)
