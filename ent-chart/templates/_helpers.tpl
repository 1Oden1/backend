{{/*
  ============================================================
  ENT Salé — _helpers.tpl
  ============================================================
*/}}

{{/* Nom du chart */}}
{{- define "ent.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Namespace cible */}}
{{- define "ent.namespace" -}}
{{- .Values.global.namespace | default "ent-sale" }}
{{- end }}

{{/* Labels standards Kubernetes */}}
{{- define "ent.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Labels de sélection pour un service donné */}}
{{- define "ent.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .release }}
{{- end }}

{{/* Image complète avec registry optionnel */}}
{{- define "ent.image" -}}
{{- $registry := .global.imageRegistry | default "" -}}
{{- if $registry -}}
{{ printf "%s/%s" $registry .image }}
{{- else -}}
{{ .image }}
{{- end }}
{{- end }}

{{/* Nom du secret global */}}
{{- define "ent.secretName" -}}
ent-credentials
{{- end }}

{{/* URL MySQL interne */}}
{{- define "ent.mysqlHost" -}}
{{ .Release.Name }}-mysql
{{- end }}

{{/* URL Keycloak interne */}}
{{- define "ent.keycloakURL" -}}
http://keycloak:8080
{{- end }}

{{/* URL RabbitMQ interne */}}
{{- define "ent.rabbitmqURL" -}}
amqp://$(RABBITMQ_USER):$(RABBITMQ_PASSWORD)@{{ .Release.Name }}-rabbitmq:5672/
{{- end }}

{{/* URL Cassandra interne */}}
{{- define "ent.cassandraHost" -}}
{{ .Release.Name }}-cassandra
{{- end }}

{{/* URL MinIO interne */}}
{{- define "ent.minioEndpoint" -}}
{{ .Release.Name }}-minio:9000
{{- end }}

{{/* URL Ollama interne */}}
{{- define "ent.ollamaURL" -}}
http://ollama:11434
{{- end }}
