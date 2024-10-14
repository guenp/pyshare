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

You can easily find your dataframes by `name` or any of the attributes you specified:

```python
# any one of these wll give you the elstar table
df = share.get(name="elstar")
df = share.get(flavor="sweet/sharp")
df = share.get(country="The Netherlands")

# this will get you the granny smith table
df = share.get(country="Australia")

# get just the attributes for the elstar dataframe
share["elstar"].attrs

# get a table of all attributes
share.df()
```

Happy sharing!
