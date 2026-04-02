from typing import Literal, get_args

TableName = Literal["conversations", "votes", "reactions"]
TABLE_NAMES: tuple[TableName, ...] = get_args(TableName)
