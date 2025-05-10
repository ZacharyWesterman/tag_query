# A DSL for robust querying of tags in MongoDB

This module converts a text query into a dict that can be directly used in a MongoDB query of a string array field.

To get started, include this repo as a submodule in your project. Then you can use it directly:
```py
from tag_query import parse, exceptions

try:
  mongo_query = parse('value1 and value2').output('field_name')
except exceptions.ParseError as e:
  print(e)
  exit(1)

print(mongo_query) #will output -> {'$and': [{'field_name': 'value1'}, {'field_name': 'value2'}]}
```
---
# Syntax

OPERATOR: any of (`and`,`+`), (`or`,`/`), (`not`,`-`)
FUNCTION: any of (`eq`,`equals`,`exact`,`exactly`), (`lt`,`fewer`,`below`), (`gt`,`greater`,`above`), (`le`,`max`,`maximum`), (`ge`,`min`,`minimum`)
LPAREN: `(`
RPAREN: `)`
STRING: without quotes is `[a-zA-Z0-9_\.]+` (letter, number, underscore, period), inside quotes is `"(\\"|[^"])*"` (anything other that quotes)
REGEX: `\{[^\}]*\}` (anything inside curly braces `{}`)
GLOB: `*`

- Multiple strings next to each other will concatenate into a single string, with a space to separate. E.g. `str1 str2 and str3` is the same as `"str1 str2" and "str3"`.
- The `not` operator between two strings is equivalent to `and not`. E.g. `a not b` = `a and not b`.
- The GLOB operator allows simple pattern matching, e.g. `tag1*` matches anything that begins with "tag1".
- Operators and functions don't have any precedence; they are evaluated from left to right. E.g. `a and b or c and d` is the same as `((a and b) or c) and d`.
