{{- define "comparia.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "comparia.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "comparia.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "comparia.labels" -}}
helm.sh/chart: {{ include "comparia.chart" . }}
{{ include "comparia.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "comparia.selectorLabels" -}}
app.kubernetes.io/name: {{ include "comparia.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Name of the Secret every workload reads its DB/Redis/API-key env vars from:
either the chart-rendered one, or a pre-existing Secret the caller points at.
*/}}
{{- define "comparia.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-secret" (include "comparia.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "comparia.backendImage" -}}
{{- printf "%s:%s" .Values.image.backend.repository (.Values.image.backend.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{- define "comparia.frontendImage" -}}
{{- printf "%s:%s" .Values.image.frontend.repository (.Values.image.frontend.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{/*
Environment of the backend container. The purge-inactive CronJob takes the
same list: it sends the warning email and reads the session length, so a
subset would silently leave it without SMTP or with the default session length.
*/}}
{{- define "comparia.backendEnv" -}}
- name: COMPARIA_INSTANCE_NAME
  value: {{ .Values.config.instanceName | quote }}
- name: AUTH_ACCESS_POLICY
  value: {{ .Values.config.authAccessPolicy | quote }}
- name: LOG_FORMAT
  value: {{ .Values.config.logFormat | quote }}
- name: LOGDIR
  value: "/data"
- name: VOTES_OBJECTIVE
  value: {{ .Values.config.votesObjective | quote }}
- name: CACHE_ENABLED
  value: {{ .Values.config.cache.enabled | quote }}
- name: CACHE_PROBABILITY
  value: {{ .Values.config.cache.probability | quote }}
- name: CACHE_TTL
  value: {{ .Values.config.cache.ttl | quote }}
- name: CACHE_MAX_RESPONSES
  value: {{ .Values.config.cache.maxResponses | quote }}
{{- if .Values.config.sentryDsn }}
- name: SENTRY_DSN
  value: {{ .Values.config.sentryDsn | quote }}
- name: SENTRY_ENVIRONMENT
  value: {{ .Values.config.sentryEnvironment | quote }}
{{- end }}
- name: ADMIN_EMAILS
  value: {{ .Values.config.adminEmails | toJson | quote }}
- name: AUTH_DOMAIN_ALLOWLIST
  value: {{ .Values.config.auth.domainAllowlist | toJson | quote }}
- name: AUTH_SESSION_LENGTH_DAYS
  value: {{ .Values.config.auth.sessionLengthDays | quote }}
- name: DISPLAY_CURRENCY
  value: {{ .Values.config.currency.display | quote }}
{{- if .Values.config.currency.rateFromUsd }}
- name: DISPLAY_CURRENCY_RATE_FROM_USD
  value: {{ .Values.config.currency.rateFromUsd | quote }}
{{- end }}
- name: EXCHANGE_RATE_API_URL
  value: {{ .Values.config.currency.exchangeApiUrl | quote }}
- name: EXCHANGE_RATE_CACHE_SECONDS
  value: {{ .Values.config.currency.exchangeCacheSeconds | quote }}
{{- if .Values.config.appUrl }}
- name: COMPARIA_APP_URL
  value: {{ .Values.config.appUrl | quote }}
{{- end }}
{{- if .Values.config.emailFrom }}
- name: EMAIL_FROM
  value: {{ .Values.config.emailFrom | quote }}
{{- end }}
- name: EMAIL_FROM_NAME
  value: {{ .Values.config.emailFromName | quote }}
{{- if .Values.config.smtp.host }}
- name: SMTP_HOST
  value: {{ .Values.config.smtp.host | quote }}
- name: SMTP_PORT
  value: {{ .Values.config.smtp.port | quote }}
{{- end }}
{{- with .Values.backend.extraEnv }}
{{ toYaml . }}
{{- end }}
{{- end -}}
