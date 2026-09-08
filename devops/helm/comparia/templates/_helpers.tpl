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
