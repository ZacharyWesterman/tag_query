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

All query expressions are case-insensitive; that is, the mongodb query is always output in lowercase.
The only exception is the field name, which *is* case-sensitive.
Also, note that query expressions are evaluated from left to right, unless otherwise denoted by parentheses.
So `a and b or c` is the same as `(a and b) or c`, and `a or b and c` is  the same as `(a or b) and c`.

The following is the entire syntax specification:
```flex
expression := binary

binary :=
  | binary (`and`|`+`) value
  | binary (`or`|`/`) value
  | binary (`not`|`-`) value
  | value

value :=
  | `(` expression `)`
  | `not` value
  | function
  | glob
  | regex
  | tag

function :=
  | (`eq`|`equal`|`equals`|`exact`|`exactly`|`=`) number
  | (`ge`|`min`|`minimum`|`>=`) number
  | (`le`|`max`|`maximum`|`<=`) number
  | (`lt`|`fewer`|`below`|`<`) number
  | (`gt`|`greater`|`above`|`>`) number

glob :=
  | tag `*`
  | `*` tag
  | `*` tag `*`

tag := literal+

regex := `\{[^\}]*\}`

literal :=
  | `[a-z0-9_\.]+`
  | `"(\\"|[^"])*"`

number := `[0-9]+`
```

## Parentheses

In some cases, left-to-right parsing may not be wanted, so parentheses can be used to group expressions together in a precise order.
For example, `a or (b and not c)` is different than `a or b and not c` (the latter is equivalent to `(a or b) and not c`).

## Tags

Any non-keyword, non-function, non-special-character text is a single tag.
Additionally, any text inside double quotes (`"`) is a tag.
If multiple tags are adjacent, they are concatenated together into a single tag, using a single space for the delimiter.

So for example, `some_tag`, `ThisIsATag123` and `"another tag"` each count as a single tag (but keep in mind they're case-insensitive!),
and `tag1 and tag2 tag3` is the same as `"tag1" and "tag2 tag3"`.

### Globbing

The Glob operator (`*`) may be used for simple pattern matching. E.g. `*test*` will match any tag that begins or ends with "test", such as "contested". `*test` or `test*` are also valid, and match tags that end and begin with "test", respectively.
Note that only plain text tags can have globbing applied; no regex or any compound expressions.

### Regex

Any string inside curly braces is interpreted as a regex pattern. E.g. `{^[A-Za-z0-9]+$}` matches any purely alphanumeric tag.

## Operators

Operators select based on the contents of a field.

- `and`, `+`: Require *both* operands to be true. E.g. `tag1 and tag2` or `tag1 + tag2` means that the field must contain both "tag1" and "tag2".
- `or`, `/`: Require *either* of the operands to be true. E.g. `tag1 or tag2` or `tag1 / tag2` means that the field must contain "tag1" or "tag2" (or both!). 
- `not`, `-`: Invert the selection. E.g. `not tag1` means that the field must **not** contain "tag1", and `not (tag1 and tag2)` means it must not contain both "tag1" and "tag2", but it may contain one of them, or neither.
  - Note that in a binary expression, `not` can mean `and not`. For example `tag1 not tag2` or `tag1 - tag2` is the same as `tag1 and not tag2`.

## Functions

Instead of selecting the contents of a field, functions select based on *how many* values the field has.

- `eq`,`equals`,`exact`,`exactly`, `=`: Require the field to have *exactly* that many tags. E.g. `exactly 5`.
- `lt`,`fewer`,`below`, `<`: Require the field to have *fewer than* that many tags. E.g. `fewer 5`.
- `gt`,`greater`,`above`, `>`: Require the field to have *more than* that many tags. E.g. `greater 5`.
- `le`,`max`,`maximum`, `<=`: Require the field to have *at most* that many tags. E.g. `maximum 5`.
- `ge`,`min`,`minimum`, `>=`: Require the field to have *at least* that many tags. E.g. `minimum 5`.

# Optimizations

In certain trivial cases, the parser will optimize queries.
For example, `a and b and a` has a redundant value `a`, so it will be optimized into just `a and b`.
Likewise, `a or not a and not b` would be optimized into `not b`, because `a or not a` just selects everything.
As for functions, they may be optimized away if their range includes all numbers (e.g. `< 5 or >= 5`), and redundant
ranges will be removed (e.g. `> 2 or = 5` is the same as just `> 2`).

# Contradictions

Any queries that are obviously contradictory are not allowed and will raise an error.
For example, `a and not a` can never match any documents, so it's considered an error.
Likewise, expressions like `> 3 and < 2` are impossible and also raise an error.

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
| `exactly 3`                     | `{'field_name': {'$size': 3}}`                                                                                 |
| `fewer 2`                       | `{'field_name.1': {'$exists': False}}`                                                                         |
| `minimum 5`                     | `{'field_name.4': {'$exists': True}}`                                                                          |
| `tag1 or (tag2 and not tag3)`   | `{'$or': [{'field_name': 'tag1'}, {'$and': [{'field_name': 'tag2'}, {'field_name': {'$ne': 'tag3'}}]}]}` |

You can use any of these expressions with `compile_query(expression, field='field_name')`.
