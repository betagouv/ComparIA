import { env } from '$env/dynamic/private'

export const serverMatomo = () => ({
  MATOMO_URL: env.MATOMO_URL ?? '',
  MATOMO_ID: env.MATOMO_ID ?? ''
})
