import glob
import json
from pathlib import Path

from pydantic import BaseModel, RootModel

from utils.utils import read_json

CURRENT_FOLDER = Path(__file__).parent
FRONTEND_EXPORT_PATH = (
    CURRENT_FOLDER.parent.parent
    / "frontend"
    / "src"
    / "lib"
    / "generated"
    / "suggestions.ts"
)

LOCALE_FILES = {
    path.split("/")[-1].replace(".json", ""): Path(path)
    for path in glob.glob(str(CURRENT_FOLDER) + "/*.json")
}
ALL_LOCALES = set(LOCALE_FILES.keys())


class SuggestionCategory(BaseModel):
    title: str
    description: str
    icon: str
    tooltip: str | None = None
    suggestions: list[str]


# Don't forget to reflects Category type changes to exported TS type
TS_TYPE = "export type SuggestionCategory = { title: string; description: string; icon: string; tooltip?: string; suggestions: string[] }\n"


Categories = RootModel[list[SuggestionCategory]]


def main():
    categories = {
        locale: Categories(read_json(path)).model_dump(exclude_none=True)
        for locale, path in LOCALE_FILES.items()
    }

    FRONTEND_EXPORT_PATH.write_text(
        TS_TYPE
        + f"export const SUGGESTIONS: Record<{' | '.join([f"'{locale}'" for locale in LOCALE_FILES.keys()])}, SuggestionCategory[]> = {json.dumps(categories, ensure_ascii=False)}"
    )


if __name__ == "__main__":
    main()
