import glob
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, RootModel, field_serializer

from utils.utils import FRONTEND_GENERATED_DIR, read_json, write_json

CURRENT_DIR = Path(__file__).parent
FRONTEND_EXPORT_FILE = FRONTEND_GENERATED_DIR / "news.json"

LOCALE_FILES = {
    path.split("/")[-1].replace(".json", ""): Path(path)
    for path in glob.glob(str(CURRENT_DIR) + "/*.json")
}
ALL_LOCALES = set(LOCALE_FILES.keys())


class News(BaseModel):
    kind: Literal["resource", "talk", "media"]
    subKind: str
    title: str
    desc: str
    imgSrc: str
    href: str | None = None
    date: datetime | None = None
    linkLabel: str | None = None
    pinned: bool | None = None

    @field_serializer("date")
    def serialize_dt(self, date: datetime, _info):
        return date.timestamp()


# TODO generate TS types

NewsList = RootModel[list[News]]


def main():
    # news = {
    #     locale: NewsList(read_json(path)).model_dump(exclude_none=True)
    #     for locale, path in LOCALE_FILES.items()
    # }

    write_json(
        FRONTEND_EXPORT_FILE,
        NewsList(read_json(LOCALE_FILES["fr"])).model_dump(exclude_none=True),
    )


if __name__ == "__main__":
    main()
