# A DSL for robust querying of tags in MongoDB

This module converts a text query into a dict that can be directly used in a MongoDB query of a string array field.

To get started, install this package with `python3 -m pip install tag_query`.

## Example Usage
To query a collection for any documents for which the field `field_name` contains `value1` and `value2`:
```py
from tag_query import compile_query, exceptions

try:
  mongo_query = compile_query(
    expression = 'value1 and value2',
    field = 'field_name'
  )
  # Or just `compile_query('value1 and value2', 'field_name')`
except exceptions.ParseError as e:
  print(e)
  exit(1)

print(mongo_query) #will output -> {'$and': [{'field_name': 'value1'}, {'field_name': 'value2'}]}
```
---
# Syntax

First, it's important to note that a tag query expression has no precedence;
expressions are evaluated from left to right, unless otherwise demarcated by parentheses.

- TAG: case-sensitive
  - simple: Any non-keyword, non-function, alphanumeric text. `some_tag` and `ThisIsATag123` both count.
  - quoted: Any string of text inside double quotes. `"tag-with-dashes and operator text"` is a *single* tag.
  - regex: Any string inside curly braces. `{^[A-Za-z0-9]+$}` matches any purely alphanumeric tag.
  - CAVEATS for simple and quoted tags:
    - If placed next to each other without an operator between them, the tags will concatenate with a single space as the delimiter. E.g. `tag1 and tag2 tag3` is the same as `"tag1" and "tag2 tag3"`
    - The Glob operator (`*`) may be used for simple pattern matching. E.g. `*test*` will match any tag that begins or ends with "test", such as "contested". `*test` or `test*` are also valid, and match tags that end and begin with "test", respectively.
- OPERATOR: case-insensitive
  - `and`, `+`: Require *both* values to exist. `tag1 and tag2` or `tag1 + tag2`
  - `or`, `/`: Require *at least 1* value to exist. `tag1 or tag2` or `tag1 / tag2`
  - `not`, `-`: Invert the selection. `not tag1` or `not (tag1 and tag2)`
    - In a binary expression, `not` can equal `and not`. For example `tag1 not tag2` or `tag1 - tag2`
- FUNCTION: case-insensitive
  - `eq`,`equals`,`exact`,`exactly`, `=`: Require the document to have *exactly* that many tags. `exactly 5`
  - `lt`,`fewer`,`below`, `<`: Require the document to have *fewer than* that many tags. `fewer 5`
  - `gt`,`greater`,`above`, `>`: Require the document to have *more than* that many tags. `greater 5`
  - `le`,`max`,`maximum`, `<=`: Require the document to have *at most* that many tags. `maximum 5`
  - `ge`,`min`,`minimum`, `>=`: Require the document to have *at least* that many tags. `minimum 5`
- PARENTHESES:
  - `(`, `)`: Controls order of operations. `a + (b - c)` is different from `(a + b) - c` (the latter is the same as `a + b - c`. remember: left to right).

---
# Examples

Here are some example tag queries and their corresponding outputs. The outputs can be directly passed to MongoDB as selection criteria.
| Query Expression                | MongoDB Query Output                                                                                     |
|---------------------------------|----------------------------------------------------------------------------------------------------------|
| `tag1 and tag2`                 | `{'$and': [{'field_name': 'tag1'}, {'field_name': 'tag2'}]}`                                             |
| `tag1 or tag2`                  | `{'$or': [{'field_name': 'tag1'}, {'field_name': 'tag2'}]}`                                              |
| `not tag1`                      | `{'field_name': {'$ne': 'tag1'}}`                                                                        |
| `tag1 and not tag2`             | `{'$and': [{'field_name': 'tag1'}, {'field_name': {'$ne': 'tag2'}}]}`                                    |
| `"tag with spaces"`             | `{'field_name': 'tag with spaces'}`                                                                      |
| `three tags concatenated`       | `{'field_name': 'three tags concatenated'}`                                                              |
| `{^foo.*}`                      | `{'field_name': {'$regex': '^foo.*'}}`                                                                   |
| `*test*`                        | `{'field_name': {'$regex': 'test'}}`                                                                     |
| `exactly 3`                     | `{'tags': {'$size': 3}}`                                                                                 |
| `fewer 2`                       | `{'tags.1': {'$exists': False}}`                                                                         |
| `minimum 5`                     | `{'tags.4': {'$exists': True}}`                                                                          |
| `tag1 or (tag2 and not tag3)`   | `{'$or': [{'field_name': 'tag1'}, {'$and': [{'field_name': 'tag2'}, {'field_name': {'$ne': 'tag3'}}]}]}` |

You can use any of these expressions with `compile_query(expression, field='field_name')`.
