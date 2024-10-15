# PyShare: A Python Sharing library for DataFrames

This is a library for easy sharing of Python DataFrame objects. It's powered by DuckDB. 🦆

## How to install

```bash
pip install pyshare-lib
```

## Example usage

```python
import pandas as pd
from pyshare import Share

share = Share("apples", public=True)

df = pd.DataFrame({"tree_id": ["alice", "bob"], "bud_percentage": [42.1, 39.3]})
df.attrs = {"flavor": "sweet/sharp", "country": "The Netherlands"}
share["elstar"] = df

df = pd.DataFrame({"tree_id": ["charlie", "dora"], "bud_percentage": [93.1, 87.3]})
df.attrs = {"flavor": "tart", "country": "Australia"}
share["granny smith"] = df

share
```

Output:

```bash
Share(name="apples", path="md:_share/apples/2fb46588-de57-4a24-9e85-d8cf7ef78be1", public=True, auto_update=True)
┌──────────────┬──────────────┬────────────────┬─────────────┬─────────────────┐
│     name     │ column_count │ estimated_size │   flavor    │     country     │
│   varchar    │    int64     │     int64      │   varchar   │     varchar     │
├──────────────┼──────────────┼────────────────┼─────────────┼─────────────────┤
│ elstar       │            2 │              2 │ sweet/sharp │ The Netherlands │
│ granny smith │            2 │              2 │ tart        │ Australia       │
└──────────────┴──────────────┴────────────────┴─────────────┴─────────────────┘
```

```python
from pyshare import Share

share = Share(name="apples", path="md:_share/apples/2fb46588-de57-4a24-9e85-d8cf7ef78be1", public=True, auto_update=True)
df = share.get(flavor="sweet/sharp")

df.attrs
```

Output:

```bash
{'name': 'elstar', 'flavor': 'sweet/sharp', 'country': 'The Netherlands'}
```


## Configuration

Each share creates a DuckDB database, either on your local machine or on MotherDuck. By default, your shares are saved under `~/.pyshare/data`.

To override where local files are stored, set the environment variable `PYSHARE_PATH`.

To use MotherDuck, export your MotherDuck [token](https://app.motherduck.com/token-request?appName=pyshare) to an environment variable `MOTHERDUCK_TOKEN`.

## Fetching and updating data

You can easily find your dataframes by `name` or any of the attributes you specified:

```python
# any one of these wll give you the elstar table
df = share["elstar"]
df = share.get(name="elstar")
df = share.get(flavor="sweet/sharp")
df = share.get(country="The Netherlands")

# this will get you the granny smith table
df = share["granny smith"]
df = share.get(country="Australia")

# get all matches for a field
for df in share.get_all(tree="large"):
    print(df.attrs)

# get a dataframe of all attributes
share.df()
```

You can update your dataframe like so, which won't update the attributes unless you specify `df.attrs`:

```python
df = pd.DataFrame({"tree_id": ["alice", "bob", "eva"], "age": ["young", "old", "ancient"]})
share["elstar"] = df
```

To overwrite or update the attributes without updating the table, run:

```python
# overwrite
share.attrs["elstar"] = {"parentage": ["Ingrid Marie", "Golden Delicious"]}

# update
share.attrs["elstar"]["parentage"] = ["Ingrid Marie", "Golden Delicious"]
share.attrs["elstar"].update({"parentage": ["Ingrid Marie", "Golden Delicious"]})
```

Happy sharing!
