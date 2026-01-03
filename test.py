import uuid
from src.jsonplusplus import detect_type

tests = [
    [1, 2, 3],                                 # uint8
    [-1, 10],                                  # int8
    [1.23, 2.1],                               # float16
    [True, False],                             # bool
    ["A", "B", "A"],                           # enum
    ["2024-12-30"],                            # date
    ["2024-12-30T12:34:56"],                   # datetime
    [str(uuid.uuid4()), str(uuid.uuid4())],    # uuid
    [None, 1, 2],                              # nullable<uint8>
    [b"\x00\xFF"],                             # binary
    ["apple", "banana", "apple", "apple"],     # string_dict (30% répétitions)
    ["foo", "bar", "baz", "qux", "quux"],      # string (trop de valeurs uniques)
    [{"a": 1}, {"b": 2}],                      # json (fallback)
    [None, None],                              # nullable<unknown> (seulement des None)
]

# Affichage des résultats

for sample in tests:
    print(sample, "=>", detect_type(sample))
