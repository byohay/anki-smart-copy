# Anki smart copy

Smart copy allows you to intelligently copy contents of one note to another. It's highly flexible and configurable.

Supports Anki>=2.1.20.

## Why?

I used a note type (model) that's most convenient for me to use, but it had no content. I had to create notes and fill them with content. Other decks out there have the content I need, but I had to copy the content manually for every new note.

That's why I created smart copy: To automatically copy fields from another note, and allow some manipulation on the copied text to save me even more manual work.

## Getting started

First, you need to configure the name of the field that the plugin identifies as the subject for searching. When the field loses focus, it will start searching other notes and copy whatever it can find, based on the configuration described below. There are currently two kinds of configurations:

### Whole text search

Searches the whole text of the subject field in other notes, with to the following parameters:

- `field_name_to_copy_from`:

### Per character search

Searches per-character of the subject field in other notes (Each character can be found in a different note), with to the following parameters:

- `model_name` (Note type): Type of the note to copy the text from. If a note with this type wasn't found, no copy will occur.
- `field_name_to_copy_from`: Name of the field to copy the text from. If a field with this name wasn't found, no copy will occur.
- `filter_characters`: A function used to filter characters to search for. Returns `True` if the character should be searched for, `False` otherwise. Doesn't filter any character by default.
- `field_names_to_copy_to`: A list of field names in the currently edited note. Each field is a destination for a character that was searched for (i.e. a character filtered by `filter_characters`). If the number of fields here is shorter than the list of characters to search for, only the characters up to the number of fields will be copied.
