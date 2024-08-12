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

The Ayon Usd resolver has a feature we call pinning support. This allows storing
the current state of an Usd stage in a file to load the data quickly and without
server interaction on a Farm or any distributed system that might overwhelm or
impact the server performance.

The rest of this can be found in the pinning support Branch
