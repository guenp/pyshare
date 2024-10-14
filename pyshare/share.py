"""
PyShare main module
"""

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from warnings import warn

import duckdb
from pandas import DataFrame

DEFAULT_PYSHARE_PATH = Path(os.path.expanduser("~/.pyshare"))
MEMORY = ":memory:"
NAME_ATTR = "name"
MD = "md:"


def is_motherduck(path: str | Path | None = None):
    if path is None:
        return "MOTHERDUCK_TOKEN" in os.environ
    return MD in str(path)


def get_path(name: str):
    if is_motherduck():
        return f"md:{name}"
    return DEFAULT_PYSHARE_PATH / "data" / f"{name}.db"


class _ShareAttrs:
    def __init__(self, con: duckdb.DuckDBPyConnection):
        self._con = con
        self._con.sql("CREATE SCHEMA IF NOT EXISTS _pyshare")
        self._con.sql("CREATE TABLE IF NOT EXISTS _pyshare.attrs (name VARCHAR, values JSON)")

    def __setitem__(self, key: str, value: DataFrame):
        self.set(name=key, attrs=value)

    def __getitem__(self, key: str) -> DataFrame:
        return self.get(name=key)

    def set(self, name: str, attrs: dict[str, Any]):
        self._con.sql(f"INSERT INTO _pyshare.attrs VALUES ('{name}', '{json.dumps(attrs)}')")

    def get(self, name: str) -> DataFrame:
        res = self._con.sql(f"SELECT values FROM _pyshare.attrs WHERE name = '{name}'").fetchone()
        if res is not None:
            return json.loads(res[0])


class Share:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path or get_path(name)
        if path != MEMORY and not is_motherduck(path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif is_motherduck(path):
            with duckdb.connect(MD) as con:
                con.sql(f"CREATE DATABASE IF NOT EXISTS {self.name}")
        self._con = duckdb.connect(database=path)
        self._attrs = _ShareAttrs(con=self._con)

    def __setitem__(self, key: str, value: DataFrame):
        self.set(name=key, data=value)

    def __getitem__(self, key: str) -> DataFrame:
        return self.get(name=key)

    def set(self, data: DataFrame, name: str):
        self._con.sql(f"""CREATE TABLE "{name}" AS (SELECT * FROM data)""")
        if data.attrs is not None:
            if NAME_ATTR in data.attrs and data.attrs[NAME_ATTR] != name:
                warn(f"Ignoring 'name' attribute in attrs: DataFrame name is already set to {name}")
            self._attrs.set(name=name, attrs=data.attrs)

    def get_all(self, **kwargs) -> Generator[DataFrame, Any, None]:
        return self._where(**kwargs)

    def get(self, name: str | None = None, **kwargs) -> DataFrame:
        if name is None:
            return next(self._where(**kwargs))
        else:
            df = self._con.sql(f"""SELECT * FROM "{name}";""").df()
            df.attrs = self._attrs.get(name=name)
            df.attrs[NAME_ATTR] = name
            return df

    def _where(self, **kwargs):
        filters = [f"values->>'$.{key}' = '{value}'" for key, value in kwargs.items()]
        filter_sql = " AND ".join(filters)
        res = self._con.sql(f"""SELECT name FROM _pyshare.attrs WHERE ({filter_sql})""").fetchall()
        if len(res) > 0:
            for _res in res:
                (name,) = _res
                yield self.get(name)

    def set_with_attrs(self, data: DataFrame, name: str, attrs: dict[str, Any] | None = None):
        attrs = attrs or data.attrs
        data.attrs = attrs
        self.set(data=data, name=name)

    def show(self):
        res = self._con.sql("SELECT json_group_structure(values) FROM _pyshare.attrs").fetchone()
        if res is not None and res[0] is not None:
            json_structure = res[0]
            query = f"""
            WITH attrs_ AS (
                SELECT
                    name,
                    json_transform(values, '{json_structure}') AS values
                    FROM _pyshare.attrs
            ),
            tables AS (
                SELECT
                    table_name,
                    column_count,
                    estimated_size
                    FROM duckdb_tables()
                    WHERE schema_name = 'main'
            )
            SELECT table_name AS name, column_count, estimated_size, values.*
            FROM tables JOIN attrs_ ON table_name = name
            """
            return self._con.sql(query)

    def df(self) -> DataFrame:
        show = self.show()
        if show is not None:
            df = show.df()
            df.attrs[NAME_ATTR] = self.name
            return df
        return DataFrame()

    def __repr__(self) -> str:
        share_repr = f"Share(name={self.name})"
        share_overview = self.show()
        if share_overview is not None:
            return f"{share_repr}\n" + share_overview.__repr__()
        return share_repr


def create_share(name: str, path: str | None = None) -> Share:
    path = path or get_path(name)
    return Share(name=name, path=path)
