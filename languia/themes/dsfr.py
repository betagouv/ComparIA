from __future__ import annotations
from typing import Iterable
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class DSFR(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.neutral,
        secondary_hue: colors.Color | str = colors.neutral,
        neutral_hue: colors.Color | str = colors.neutral,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_none,
        text_size: sizes.Size | str = sizes.text_lg,
        button_large_text_weight: str = "normal",
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            "Marianne",
            "Arial",
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            "Marianne",
            "Arial",
            "ui-sans-serif",
            "sans-serif",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        super().set(button_large_text_weight="400", block_border_width="0", block_border_color="transparent")


        # super().set(
        #     block_border_width='2px',
        #     block_border_width_dark='2px',                        
        #     block_info_text_size='*text_md',
        #     block_info_text_weight='500',
        #     block_info_text_color='#474a50',
        #     block_label_background_fill='*background_fill_secondary',
        #     block_label_text_color='*neutral_700',
        #     block_title_text_color='black',
        #     block_title_text_weight='600',
        #     block_background_fill='#fcfcfc',
        #     body_background_fill='*background_fill_secondary',
        #     body_text_color='black',
        #     background_fill_secondary='#f8f8f8',
        #     border_color_accent='*primary_50',
        #     border_color_primary='#ededed',
        #     color_accent='#7367f0',
        #     color_accent_soft='#fcfcfc',
        #     layout_gap='*spacing_xl',
        #     panel_background_fill='#fcfcfc',
        #     section_header_text_weight='600',
        #     checkbox_background_color='*background_fill_secondary',
        #     input_background_fill='white',        
        #     input_placeholder_color='*neutral_300',
        #     loader_color = '*primary_50',        
        #     slider_color='#7367f0',
        #     table_odd_background_fill='*neutral_100',
        #     button_small_radius='*radius_sm',
        #     button_primary_background_fill='linear-gradient(to bottom right, #7367f0, #9c93f4)',
        #     button_primary_background_fill_hover='linear-gradient(to bottom right, #9c93f4, #9c93f4)',
        #     button_primary_background_fill_hover_dark='linear-gradient(to bottom right, #5e50ee, #5e50ee)',
        #     button_primary_border_color='#5949ed',
        #     button_primary_text_color='white'
        # )