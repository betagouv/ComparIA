import { consumeAltchaToken } from '$lib/captcha.svelte'
import { api } from '$lib/fastapi-client'
import { getLocale } from '$lib/i18n/runtime'

export type TranscribeResponse = {
  text: string
  // Null when the instance keeps nothing, so there is no id to send on.
  recording_id: string | null
}

export type VoiceRecorderOptions = {
  maxSeconds: number
  onText: (text: string, recordingId: string | null) => void
  onError: (message: string) => void
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

export function useVoiceRecorder({ maxSeconds, onText, onError }: VoiceRecorderOptions) {
  let recording = $state(false)
  let transcribing = $state(false)
  let seconds = $state(0)

  let recorder: MediaRecorder | null = null
  let timer: ReturnType<typeof setInterval> | null = null
  let startedAt = 0

  function stopTimer() {
    if (timer) clearInterval(timer)
    timer = null
  }

  function releaseTracks() {
    recorder?.stream.getTracks().forEach((track) => track.stop())
    recorder = null
  }

  async function send(audio: Blob, durationMs: number) {
    transcribing = true
    try {
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
      if (result.text) onText(result.text, result.recording_id)
      else onError('voice.empty')
    } catch (e) {
      console.error(e)
      onError('voice.failed')
    } finally {
      transcribing = false
    }
  }

  async function start() {
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      console.error(e)
      onError('voice.denied')
      return
    }

    const chunks: Blob[] = []
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recorder.ondataavailable = (e) => chunks.push(e.data)
    recorder.onstop = () => {
      const durationMs = Date.now() - startedAt
      releaseTracks()
      send(new Blob(chunks, { type: 'audio/webm' }), durationMs)
    }

    startedAt = Date.now()
    seconds = 0
    recording = true
    recorder.start()

    timer = setInterval(() => {
      seconds = Math.floor((Date.now() - startedAt) / 1000)
      // Stops itself rather than letting someone hold a paid endpoint open,
      // and keeps every recording clear of the provider's own cut-off.
      if (seconds >= maxSeconds) stop()
    }, 250)
  }

  function stop() {
    stopTimer()
    recording = false
    recorder?.stop()
  }

  return {
    get recording() {
      return recording
    },
    get transcribing() {
      return transcribing
    },
    get seconds() {
      return seconds
    },
    toggle() {
      if (recording) stop()
      else start()
    },
    cancel() {
      stopTimer()
      recording = false
      if (recorder) {
        recorder.onstop = null
        recorder.stop()
        releaseTracks()
      }
    }
  }
}
