schema = {
  "type": "map",
  "mapping": {
    "secret": {
      "type": "str",
      "required": True
    },
    "commands": {
      "type": "seq",
      "required": True,
      "sequence": [
        {
          "type": "str"
        }
      ]
    },
    "after_failure": {
      "type": "seq",
      "sequence": [
        {
          "type": "str"
        }
      ]
    },
    "image": {
      "required": True,
      "type": "str"
    },
    "env": {
      "allowempty": True,
      "type": "map",
      "matching-rule": "all",
      "mapping": {
        "regex;(.*)": {
          "type": "any"
        }
      }
    },
    "repository": {
      "type": "map",
      "mapping": {
        "origin": {
          "type": "str"
        },
        "branch": {
          "type": "str"
        },
        "commit": {
          "type": "str"
        },
      }
    }
  }
}
