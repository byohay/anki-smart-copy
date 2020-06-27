# READ THIS FIRST!!!

#### It is highly recommended to refer to the examples found in the plugin's documentation page:

## Notes

- The plugin doesn't copy content that already appears in the destination field/s.

## Schema description

You will need to understand regular expression syntax to work with some of the fields. Please refer to: https://realpython.com/regex-python/. Or search Google for "Python regex".

* `subjectField`: Name of the field that you want to search for. Currently only one subject field is supported.

* `wholeTextSearchConfigurations`: A list of whole text search configurations, each defines a field to copy from another note to the currently edited one.
    * `noteType`: Type of the note in which to search the text that is found in `subjectField`.
    * `sourceField`: Name of the field from which to copy the contents.
    * `destinationField`: Name of the field in the currently edited note to copy the contents into.
    * `blankOutWordAfterCopy`: If the text in the subject field appears in the text of `fieldToCopyFrom` and this flag is set to `true`, then this sub-text will be replaced with `_` in `fieldToCopyTo`. See also `blankOutRegex`.
    * `copyOnlyIfEmpty`: If this is set to `true`, copies the text only if `destinationField` is empty.
    * `textToRemoveRegex`: Removes all the instances that match this regular expression from the text in `sourceField` before copying it to `destinationField`. Defaults to not removing any text.
    * `blankOutTextRegex`: Instead of blanking out the exact text in `subjectField`, blank out the first match of this regex in the text of `destinationField`. `blankOutWordAfterCopy` must be set to `true` for this to work. Defaults to not manipulating the text.

* `perCharacterSearchConfigurations`: A list of per-character search configurations, each defines a field to copy from another note to the currently edited one. Each
    * `noteType`: Type of the note in which to search the character.
    * `sourceField`: Name of the field from which to copy the content.
    * `destinationFields`: A list of fields names in the currently edited note to copy the content into.
    * `copyOnlyIfEmpty`: If this is set to `true`, copies the text only if `destinationField` is empty.
    * `filterCharacters`: If specified, filters characters to search for. Currently, supports only `FILTER_KANJI`.
