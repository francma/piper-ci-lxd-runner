schema = {
  "type": "map",
  "mapping": {
    "lxd": {
      "type": "map",
      "mapping": {
        "profiles": {
          "type": "seq",
          "sequence": [
            {
              "type": "str"
            }
          ]
        },
        "endpoint": {
          "type": "str",
          "required": True
        },
        "cert": {
          "type": "str",
          "required": True
        },
        "key": {
          "type": "str",
          "required": True
        },
        "verify": {
          "type": "bool"
        }
      }
    },
    "runner": {
      "type": "map",
      "mapping": {
        "token": {
          "type": "str",
          "required": True
        },
        "interval": {
          "type": "int",
          "range": {
            "min": 1
          }
        },
        "instances": {
          "type": "int",
          "range": {
            "min": 1
          }
        },
        "endpoint": {
          "type": "str",
          "required": True
        }
      }
    },
    "logging": {
      "type": "map",
      "allowempty": True
    }
  }
}

