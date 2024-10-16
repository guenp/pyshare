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
import rich

PYSHARE_PATH = "PYSHARE_PATH"
DEFAULT_PYSHARE_PATH = Path(os.path.expanduser("~/.pyshare"))
MEMORY = ":memory:"
NAME_ATTR = "name"
MD = "md:"
ORGANIZATION = "ORGANIZATION"
UNRESTRICTED = "UNRESTRICTED"
AUTOMATIC = "AUTOMATIC"
MANUAL = "MANUAL"


def is_motherduck(path: str | Path | None = None):
    if path is None:
        return "MOTHERDUCK_TOKEN" in os.environ
    return MD in str(path)


def is_share(path: str | None):
    if path is not None:
        return "md:_share" in path
    return False


def get_path(name: str):
    if PYSHARE_PATH in os.environ:
        return Path(os.path.expanduser(os.environ[PYSHARE_PATH])) / f"{name}.db"
    if is_motherduck():
        return f"{MD}{name}"
    return DEFAULT_PYSHARE_PATH / "data" / f"{name}.db"


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop("name")
        self.callback = kwargs.pop("callback")
        dict.__init__(self, name=self.name, *args, **kwargs)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.callback(self.name, self)

    def update(self, m, **kwargs):
        dict.update(self, m, **kwargs)
        self.callback(self.name, self)


class _ShareAttrs:
    def __init__(self, con: duckdb.DuckDBPyConnection, read_only: bool = False):
        self._con = con
        self.read_only = read_only
        if not read_only:
            self._con.sql("CREATE SCHEMA IF NOT EXISTS _pyshare")
            self._con.sql("CREATE TABLE IF NOT EXISTS _pyshare.attrs (name VARCHAR PRIMARY KEY, values JSON)")
        else:
            rich.print("Connecting in [bold magenta]read-only mode[/bold magenta]")

    def __setitem__(self, key: str, value: dict[str, Any]):
        self.set(name=key, attrs=value)

    def __getitem__(self, key: str) -> dict[str, Any]:
        return self.get(name=key)

    def set(self, name: str, attrs: dict[str, Any]):
        attrs_to_set = attrs.copy()
        if NAME_ATTR in attrs_to_set:
            attrs_to_set.pop(NAME_ATTR)
        self._con.sql(f"INSERT OR REPLACE INTO _pyshare.attrs VALUES ('{name}', '{json.dumps(attrs_to_set)}')")

    def get(self, name: str) -> dict[str, Any]:
        res = self._con.sql(f"SELECT values FROM _pyshare.attrs WHERE name = '{name}'").fetchone()
        if res is not None:
            return AttrDict(name=name, callback=self.set, **json.loads(res[0]))
        return AttrDict(name=name, callback=self.set)

    def show(self):
        res = self._con.sql("SELECT json_group_structure(values) FROM _pyshare.attrs").fetchone()
        if res is not None and res[0] is not None and res[0] != '"JSON"':
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
            SELECT
                table_name AS name,
                values.*
            FROM tables
            LEFT JOIN
            attrs_ ON table_name = name
            """
        else:
            # No attributes found
            query = """
            WITH tables AS (
                SELECT
                    table_name,
                    column_count,
                    estimated_size
                    FROM duckdb_tables()
                    WHERE schema_name = 'main'
            )
            SELECT
                table_name AS name
            FROM tables
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
        share_repr = f"_ShareAttrs(read_only={self.read_only})"
        share_overview = self.show()
        if share_overview is not None:
            return f"{share_repr}\n" + share_overview.__repr__()
        return share_repr


class Share:
    def __init__(self, name: str, path: str | None = None, public: bool = False, auto_update: bool = True):
        self.name = name
        self.path = path or get_path(name)
        self._access = UNRESTRICTED if public is True else ORGANIZATION
        self._update = AUTOMATIC if auto_update is True else MANUAL
        if path != MEMORY and not is_motherduck(self.path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif is_motherduck(self.path):
            with duckdb.connect(MD) as con:
                if is_share(self.path):
                    con.sql(f"ATTACH '{self.path}'")
                else:
                    con.sql(f"CREATE DATABASE IF NOT EXISTS {self.name}")
                    try:
                        res = con.sql(
                            f"""
                            CREATE SHARE IF NOT EXISTS {self.name}
                            FROM {self.name} (ACCESS {self._access} , VISIBILITY DISCOVERABLE , UPDATE {self._update});
                        """
                        )
                        self.share_url = res.fetchone()[0]
                    except duckdb.CatalogException:
                        warn("Skipping creating share")
                        pass
        self._con = duckdb.connect(database=self.path)
        self._attrs = _ShareAttrs(con=self._con, read_only=is_share(path))

    def update(self):
        self._con.sql(f"UPDATE SHARE {self.name}")

    def sql(self, query: str, *, alias: str = "", params: object = None):
        return self._con.sql(query=query, alias=alias, params=params)

    def __del__(self):
        self._con.close()
        if is_share(self.path):
            with duckdb.connect(MD) as con:
                con.sql(f"DETACH {self.name}")

    def __setitem__(self, key: str, value: DataFrame):
        self.set(name=key, data=value)

    def __getitem__(self, key: str) -> DataFrame:
        return self.get(name=key)

    def set(self, name: str, data: DataFrame):
        self._con.sql(f"""CREATE OR REPLACE TABLE "{name}" AS (SELECT * FROM data)""")
        if data.attrs:
            attrs_to_set = data.attrs.copy()
            if NAME_ATTR in data.attrs:
                warn(f"Ignoring 'name' attribute in attrs: DataFrame name is already set to {name}")
                attrs_to_set.pop(NAME_ATTR)
            self._attrs.set(name=name, attrs=attrs_to_set)

    def get_all(self, **kwargs) -> Generator[DataFrame, Any, None]:
        return self._where(**kwargs)

    def get(self, name: str | None = None, **kwargs) -> DataFrame:
        if name is None:
            gen = self._where(**kwargs)
            try:
                return next(gen)
            except StopIteration:
                return DataFrame()
        else:
            df = self._con.sql(f"""SELECT * FROM "{name}";""").df()
            df.attrs = self._attrs.get(name=name)
            return df

    def _where(self, **kwargs) -> Generator[DataFrame, Any, None] | None:
        if kwargs:
            filters = [f"values->>'$.{key}' = '{value}'" for key, value in kwargs.items()]
            filter_sql = " AND ".join(filters)
            res = self._con.sql(f"""SELECT name FROM _pyshare.attrs WHERE ({filter_sql})""").fetchall()
            if len(res) > 0:
                for _res in res:
                    (name,) = _res
                    yield self.get(name)

    def show(self):
        res = self._con.sql("SELECT json_group_structure(values) FROM _pyshare.attrs").fetchone()
        if res is not None and res[0] is not None and res[0] != '"JSON"':
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
            SELECT
                table_name AS name,
                column_count,
                estimated_size,
                values.*
            FROM tables
            LEFT JOIN
            attrs_ ON table_name = name
            """
        else:
            # No attributes found
            query = """
            WITH tables AS (
                SELECT
                    table_name,
                    column_count,
                    estimated_size
                    FROM duckdb_tables()
                    WHERE schema_name = 'main'
            )
            SELECT
                table_name AS name,
                column_count,
                estimated_size
            FROM tables
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
        if hasattr(self, "share_url"):
            path = self.share_url
        else:
            path = self.path
        share_repr = f"""Share(name="{self.name}", path="{path}")"""
        if is_share(self.path):
            share_repr += " (read-only)"
        share_overview = self.show()
        if share_overview is not None:
            return f"{share_repr}\n" + share_overview.__repr__()
        return share_repr

    @property
    def attrs(self):
        return self._attrs


def create_share(name: str, path: str | None = None) -> Share:
    path = path or get_path(name)
    return Share(name=name, path=path)
