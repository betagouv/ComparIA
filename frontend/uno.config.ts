import { FileSystemIconLoader } from '@iconify/utils/lib/loader/node-loaders'
import extractorSvelte from '@unocss/extractor-svelte'
import {
  defineConfig,
  presetIcons,
  presetTypography,
  presetWind4,
  transformerDirectives
} from 'unocss'
import { ICONS } from './src/lib/generated/models'

export default defineConfig({
  extractors: [extractorSvelte()],
  presets: [
    presetWind4({
      dark: {
        dark: '[data-fr-theme="dark"]',
        light: '[data-fr-theme="light"]'
      }
    }),
    presetTypography(),
    presetIcons({
      // https://unocss.dev/presets/icons
      collections: {
        ri: () => import('@iconify-json/ri/icons.json').then((i) => i.default),
        ai: FileSystemIconLoader('./node_modules/@lobehub/icons-static-svg/icons')
      }
    })
  ],
  transformers: [transformerDirectives()],
  theme: {
    // https://unocss.dev/config/theme
    colors: {
      white: 'var(--grey-1000-50)',
      black: 'var(--grey-0-1000)',
      primary: 'var(--blue-france-main-525)',
      'light-primary': 'var(--brand-primary-soft)',
      'very-light-primary': 'var(--brand-primary-softest)',
      secondary: 'var(--brand-secondary)',
      'secondary-text': 'var(--brand-secondary-text)',
      info: 'var(--info-425-625)',
      'light-info': 'var(--info-950-100)',
      'very-light-info': 'var(--cg-very-light-blue)',
      error: 'var(--error-425-625)',
      warning: 'var(--warning-425-625)',
      success: 'var(--green-emeraude-main-632)',
      yellow: 'var(--yellow-tournesol-850-200)',
      green: 'var(--cg-green)',
      purple: 'var(--cg-purple)',
      red: 'var(--red-marianne-425-625-active)',
      grey: 'var(--grey-425-625)',
      'dark-grey': 'var(--grey-200-850)',
      /* CUSTOM COLORS */
      'very-light-grey': 'var(--cg-very-light-grey)',
      'light-grey': 'var(--cg-light-grey)'
    },
    breakpoint: {
      sm: '36em',
      md: '48em',
      lg: '62em',
      xl: '78em',
      '2xl': '88em',
      '3xl': '115em'
    }
  },
  shortcuts: [
    {
      'cg-border': 'border-1 border-[--grey-925-125] border-solid rounded-xl',
      'c-bot-disk-a': 'w-[22px] h-[22px] rounded-full bg-purple',
      'c-bot-disk-b': 'w-[22px] h-[22px] rounded-full bg-secondary',
      'text-xxs': 'text-[10px] leading-normal'
    }
  ],
  safelist: [
    'text-primary',
    'text-secondary-text',
    'c-bot-disk-a',
    'c-bot-disk-b',
    'i-ri-dice-line',
    'i-ri-search-line',
    'i-ri-leaf-line',
    'i-ri-ruler-line',
    'i-ri-brain-2-line',
    // suggestions
    'i-ri-draft-line',
    'i-ri-clipboard-line',
    'i-ri-chat-3-line',
    'i-ri-lightbulb-line',
    'i-ri-translate-2',
    'i-ri-bowl-line',
    'i-ri-music-2-line',
    'i-ri-book-open-line',
    // cards
    'i-ri-stack-line',
    'i-ri-text-snippet',
    'i-ri-price-tag-3-line',
    'i-ri-shapes-line',
    'i-ri-copyright-line',
    'i-ri-calendar-line',
    'i-ri-government-line',
    // modalities
    'i-ri-file-text-line',
    'i-ri-image-upload-line',
    'i-ri-volume-up-line',
    'i-ri-video-line',
    ...ICONS.map((icon) => 'i-ai-' + icon)
  ]
})
