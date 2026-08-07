import { getAuthContext } from '$lib/auth.svelte'
import { consumeAltchaToken } from '$lib/captcha.svelte'
import { api } from '$lib/fastapi-client'
import { getLocale } from '$lib/i18n/runtime'

export type TranscribeResponse = {
  text: string
  // Null when the instance keeps nothing, so there is no id to send on.
  recording_id: string | null
}

/** What TextPrompt needs to offer a microphone. It holds the API call and the
 * ids, so the component itself keeps to recording and to what is on screen. */
export type VoiceInput = {
  maxSeconds: number
  /** Told to the user while recordings are kept. Empty when they are not. */
  notice: string
  transcribe: (audio: Blob, durationMs: number) => Promise<string>
}

/** Whether this browser can record at all. Checked before showing the button:
 * an offer that fails on click is worse than no offer. */
export function canRecord(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof MediaRecorder !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia
  )
}

/**
 * The voice input for one prompt box, or null where it is not on offer.
 *
 * `recordingIds` collects the recordings whose transcription is still in the
 * box. They go with the prompt on send, which is what lets the stored audio be
 * compared with the text the user actually sent.
 */
export function useVoiceInput(notice: string) {
  const auth = getAuthContext()

  let recordingIds = $state<string[]>([])

  const enabled = $derived(!!auth.config?.voice_enabled && canRecord())

  const input = $derived<VoiceInput | undefined>(
    enabled
      ? {
          maxSeconds: auth.config?.voice_max_seconds ?? 60,
          notice: auth.config?.voice_stores_audio ? notice : '',
          transcribe: async (audio, durationMs) => {
            const body = new FormData()
            body.append('audio', audio, 'recording.webm')
            body.append('altcha_token', await consumeAltchaToken())
            body.append('duration_ms', String(durationMs))
            body.append('locale', getLocale())

            // No Content-Type: the browser sets the multipart boundary itself.
            const result = await api.request<TranscribeResponse>('/arena/transcribe', {
              method: 'POST',
              body,
              headers: {}
            })
            if (result.recording_id) recordingIds.push(result.recording_id)
            return result.text
          }
        }
      : undefined
  )

  return {
    get input() {
      return input
    },
    get recordingIds() {
      return recordingIds
    },
    clear() {
      recordingIds = []
    }
  }
}
