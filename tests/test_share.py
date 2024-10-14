from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pyshare import Share, create_share


@pytest.fixture()
def path():
    return ":memory:"


@pytest.fixture()
def test_data_path():
    return Path(__file__).parent / "data"


@pytest.fixture()
def df_elstar(test_data_path):
    return pd.read_csv(test_data_path / "elstar.csv")


@pytest.fixture()
def attrs_elstar():
    return {"flavor": "sweet/sharp", "country": "The Netherlands"}


@pytest.fixture()
def df_granny_smith(test_data_path):
    return pd.read_csv(test_data_path / "elstar.csv")


@pytest.fixture()
def attrs_granny_smith():
    return {"flavor": "tart", "country": "Australia"}


def test_share(df_elstar: pd.DataFrame, path: str):
    share = Share(name="apples", path=path)
    share["elstar"] = df_elstar
    df_1 = share["elstar"]
    assert df_1.equals(df_elstar)


def test_share_attrs(df_elstar: pd.DataFrame, attrs_elstar: dict[str, Any], path: str):
    share = Share(name="apples", path=path)
    df_elstar.attrs = attrs_elstar
    share["elstar"] = df_elstar
    attrs_1 = share["elstar"].attrs
    assert attrs_1 == attrs_elstar
    share_df = share.df()
    assert share_df[share_df.flavor == "sweet/sharp"].name.values == ["elstar"]


def test_create_share(df_elstar: pd.DataFrame, attrs_elstar: dict[str, Any], path: str):
    share = create_share("apples", path)
    df_elstar.attrs = attrs_elstar
    share["elstar"] = df_elstar
    assert share["elstar"].equals(df_elstar)


def test_find(
    df_elstar: pd.DataFrame,
    attrs_elstar: dict[str, Any],
    df_granny_smith: pd.DataFrame,
    attrs_granny_smith: dict[str, Any],
    path: str,
):
    share = create_share("apples", path)
    df_elstar.attrs = attrs_elstar
    share["elstar"] = df_elstar
    df_granny_smith.attrs = attrs_granny_smith
    share["granny smith"] = df_granny_smith

    # Find DataFrame by attributes
    df = share.get(flavor="sweet/sharp")
    assert df.equals(df_elstar)

    df = share.get(flavor="tart")
    assert df.equals(df_granny_smith)
