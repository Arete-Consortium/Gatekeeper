{{/*
Expand the name of the chart.
*/}}
{{- define "eve-gatekeeper.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this
(by the DNS naming spec). If release name contains chart name it will be used
as a full name.
*/}}
{{- define "eve-gatekeeper.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "eve-gatekeeper.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "eve-gatekeeper.labels" -}}
helm.sh/chart: {{ include "eve-gatekeeper.chart" . }}
{{ include "eve-gatekeeper.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "eve-gatekeeper.selectorLabels" -}}
app.kubernetes.io/name: {{ include "eve-gatekeeper.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use.
*/}}
{{- define "eve-gatekeeper.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "eve-gatekeeper.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Name of the secret to use.
*/}}
{{- define "eve-gatekeeper.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "eve-gatekeeper.fullname" . }}-secrets
{{- end }}
{{- end }}

{{/*
PostgreSQL fullname helper.
*/}}
{{- define "eve-gatekeeper.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "eve-gatekeeper.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Redis fullname helper.
*/}}
{{- define "eve-gatekeeper.redis.fullname" -}}
{{- printf "%s-redis" (include "eve-gatekeeper.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Image reference helper.
*/}}
{{- define "eve-gatekeeper.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag }}
{{- printf "%s:%s" .Values.image.repository $tag }}
{{- end }}
