# Developer Docs

Most important Locations.

1. config
   - provides general addon config and a list of variables and functions to
     access settings across the addon.
   - also allows to get lakeFs related classes and functions in there global
     state
2. hooks
   - Ayon + Pyblish related addons and hooks.
3. standalone
   - AyonUsd standalone tools. They should be DCC agnostic.
4. utils
   - utility functions to make interaction with the addon simpler.

## Standalone

### Pinning Support.

`Standalone/Usd/pinning/pinning_file_helper.py`

The Ayon Usd resolver has a feature we call pinning support.\
This allows storing the current resolver state for an Usd stage in a file to
load the frozen stage without server interaction.

`generate_pinning_file`\
creates a pinning file JSON from a given USD stage

```py
def generate_pinning_file(
    entry_usd: str, root_info: Dict[str, str], pinning_file_path: str
):
```

Example Code:

```py
from tests.Usd.Pinning import pinning_file_helper
import ayon_api

in_usd_file = "path/to/usd/file.usd"
root_info = ayon_api.get_project_roots_for_site(os.environ.get("AYON_PROJECT_NAME"))

pinning_file_helper.generate_pinning_file(
    uri, root_info, "path/to/output_file.json")
)
```

`in_usd_file` can be everything that the AyonUsdResolver can resolve including
an URI its just important to know that what ever you use as the input must be
the input when you load the usd.\
in other words: if you use an uri to generate the pinning file you need to open
the stage with the same uri, if you use an file path you will need to do the
same.\
it is generally advised to use an URI as they will never have any system
specific data in them.
