import glob
import json
from pathlib import Path

from pydantic import BaseModel, RootModel

from utils.utils import FRONTEND_GENERATED_DIR, read_json

CURRENT_DIR = Path(__file__).parent
FRONTEND_EXPORT_FILE = FRONTEND_GENERATED_DIR / "suggestions.ts"

LOCALE_FILES = {
    path.split("/")[-1].replace(".json", ""): Path(path)
    for path in glob.glob(str(CURRENT_DIR) + "/*.json")
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

    FRONTEND_EXPORT_FILE.write_text(
        TS_TYPE
        + f"export const SUGGESTIONS: Record<{' | '.join([f"'{locale}'" for locale in LOCALE_FILES.keys()])}, SuggestionCategory[]> = {json.dumps(categories, ensure_ascii=False)}"
    )


if __name__ == "__main__":
    main()
