"""
PyShare main module
"""

import json
import os
from pathlib import Path
from typing import Any
from warnings import warn

import duckdb
from pandas import DataFrame

DEFAULT_PYSHARE_PATH = Path(os.path.expanduser("~/.pyshare"))
MEMORY = ":memory:"
NAME_ATTR = "name"


def get_path(name: str):
    if "MOTHERDUCK_TOKEN" in os.environ:
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

    def df(self) -> DataFrame:
        res = self._con.sql(
            """
            select json_group_structure(values) from _pyshare.attrs
        """
        ).fetchone()

        if res is not None:
            json_structure = res[0]

            return self._con.sql(
                f"""
            with attrs_ as (
                select
                    name,
                    json_transform(values, '{json_structure}') as values
                    from _pyshare.attrs
            )
            select name, values.* from attrs_
            """
            ).df()


class Share:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path or get_path(name)
        if path != MEMORY:
            self.path.parent.mkdir(parents=True, exist_ok=True)
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
                warn(f"Ignoring 'name' attribute in attrs: DataFrame name is set to {name}")
            self._attrs.set(name=name, attrs=data.attrs)

    def get(self, name: str | None = None, **kwargs) -> DataFrame:
        if name is None:
            return self._where(**kwargs)
        else:
            df = self._con.sql(f"""SELECT * FROM "{name}";""").df()
            df.attrs = self._attrs.get(name=name)
            df.attrs[NAME_ATTR] = name
            return df

    def _where(self, **kwargs):
        filters = [f"values->>'$.{key}' = '{value}'" for key, value in kwargs.items()]
        filter_sql = " AND ".join(filters)
        res = self._con.sql(f"""SELECT name FROM _pyshare.attrs WHERE ({filter_sql})""").fetchone()
        if res is not None:
            name = res[0]
            return self.get(name)

    def set_with_attrs(self, data: DataFrame, name: str, attrs: dict[str, Any] | None = None):
        attrs = attrs or data.attrs
        data.attrs = attrs
        self.set(data=data, name=name)

    def show(self):
        res = self._con.sql("""
            select json_group_structure(values) from _pyshare.attrs
        """
        ).fetchone()
        if res is not None:
            json_structure = res[0]
            query = f"""
            with attrs_ as (
                select
                    name,
                    json_transform(values, '{json_structure}') as values
                    from _pyshare.attrs
            ),
            tables as (
                select
                    table_name,
                    column_count,
                    estimated_size from duckdb_tables()
                    where schema_name = 'main'
            )
            select table_name as name, column_count, estimated_size, values.*
            from tables join attrs_ on table_name = name
            """
            return self._con.sql(query)

    def df(self) -> DataFrame:
        df = self.show().df()
        df.attrs[NAME_ATTR] = self.name
        return df

    def __repr__(self) -> str:
        return f"Share(name={self.name})\n" + self.show().__repr__()

def create_share(name: str, path: str | None = None) -> Share:
    path = path or get_path(name)
    return Share(name=name, path=path)
