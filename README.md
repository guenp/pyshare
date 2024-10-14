# PyShare: A Python Sharing library for DataFrames

This is a library for easy sharing of Python DataFrame objects. It's powered by DuckDB. 🦆

## Example usage

```python
from pyshare import create_share
import pandas as pd

share = create_share("apples")

# 1. create a unique dataframe
# 2. add attributes to make it easier to find the dataframe later
# 3. add the dataframe to your share
df = pd.DataFrame({"tree_id": [1, 2], "size": [2.4, 1.2], "num_apples": [234, 123], "harvest": ["plentiful", "sparse"]})
df.attrs = {"flavor": "sweet/sharp", "country": "The Netherlands"}
share["elstar"] = df

df = pd.DataFrame({"tree_id": [3, 4], "size": [3.1, 2.2], "treatment": ["irrigated", "non-irrigated"], "bud_percentage": [93.1, 87.3]})
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
│ elstar       │            4 │              2 │ sweet/sharp │ The Netherlands │
│ granny smith │            4 │              2 │ tart        │ Australia       │
└──────────────┴──────────────┴────────────────┴─────────────┴─────────────────┘
```


You can update your dataframe like so, which won't update the attributes unless you specify `df.attrs`:

```python
df = pd.DataFrame({"tree_id": [1, 2, 3], "size": [2.4, 1.2, 0.8], "num_apples": [234, 123, 40], "harvest": ["plentiful", "sparse", "baby"]})
# uncomment this to overwrite the attributes
# df.attrs = {"parentage": ["Ingrid Marie", "Golden Delicious"]}
share["elstar"] = df
```

To overwrite or update the attributes without updating the table, run:

```python
# overwrite
share.attrs["elstar"] = {"parentage": ["Ingrid Marie", "Golden Delicious"]}
# update
share.attrs["elstar"].update({"parentage": ["Ingrid Marie", "Golden Delicious"]})
```

You can easily find your dataframes by `name` or any of the attributes you specified:

```python
# any one of these wll give you the elstar table
df = share.get(name="elstar")
df = share.get(flavor="sweet/sharp")
df = share.get(country="The Netherlands")

# this will get you the granny smith table
df = share.get(country="Australia")

# get all matches for a field
share.attrs["elstar"]["tree"] = "large"
share.attrs["granny smith"]["tree"] = "large"
for df in share.get_all(tree="large"):
    print(df.attrs)

# get a dataframe of all attributes
share.df()
```

Happy sharing!
