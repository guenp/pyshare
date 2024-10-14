# PyShare: A Python Sharing library for DataFrames

This is a library for easy sharing of Python DataFrame objects. It's powered by DuckDB. 🦆

## Example usage

```python
from pyshare import create_share
import pandas as pd

share = create_share("apples")

# create a dataframe
df = pd.DataFrame({"tree_id": ["alice", "bob"], "age": ["young", "old"]})
# add attributes to make it easier to find the dataframe later
df.attrs = {"flavor": "sweet/sharp", "country": "The Netherlands"}
# add the dataframe to your share
share["elstar"] = df

# another example
df = pd.DataFrame({"tree_id": ["charlie", "dora"], "bud_percentage": [93.1, 87.3]})
df.attrs = {"flavor": "tart", "country": "Australia"}
share["granny smith"] = df
```

To inspect your share and display an overview of all dataframes and attributes, run
```
share
```

which returns:

```bash
Share(name=apples)
┌──────────────┬──────────────┬────────────────┬─────────────┬─────────────────┐
│     name     │ column_count │ estimated_size │   flavor    │     country     │
│   varchar    │    int64     │     int64      │   varchar   │     varchar     │
├──────────────┼──────────────┼────────────────┼─────────────┼─────────────────┤
│ elstar       │            2 │              2 │ sweet/sharp │ The Netherlands │
│ granny smith │            2 │              2 │ tart        │ Australia       │
└──────────────┴──────────────┴────────────────┴─────────────┴─────────────────┘
```

To get a dataframe version of the above, run
```
share.df()
```

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
