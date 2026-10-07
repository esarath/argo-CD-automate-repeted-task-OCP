{{/*
Common labels applied to every resource the chart creates.
*/}}
{{- define "team-onboarding.labels" -}}
app.kubernetes.io/part-of: gitops-platform
app.kubernetes.io/managed-by: argocd
app.kubernetes.io/instance: team-onboarding
platform/team: {{ .Values.teamName }}
helm.sh/chart: team-onboarding-{{ .Chart.Version }}
{{- end }}

{{/*
Validates teamName is a legal DNS-1123 namespace name; fails the render
otherwise so a bad value never reaches the cluster.
*/}}
{{- define "team-onboarding.validateName" -}}
{{- if not .Values.teamName -}}
{{- fail "teamName is required" -}}
{{- end -}}
{{- if not (regexMatch "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$" .Values.teamName) -}}
{{- fail (printf "teamName '%s' is not a valid DNS-1123 label" .Values.teamName) -}}
{{- end -}}
{{- if gt (len .Values.teamName) 63 -}}
{{- fail (printf "teamName '%s' exceeds 63 characters" .Values.teamName) -}}
{{- end -}}
{{- end }}

{{/*
Reserved namespaces that must never be onboarded via self-service.
*/}}
{{- define "team-onboarding.rejectReserved" -}}
{{- $reserved := list "default" "kube-system" "kube-public" "kube-node-lease"
    "openshift" "openshift-gitops" "openshift-monitoring" "openshift-apiserver"
    "openshift-ingress" "openshift-dns" "openshift-operators" -}}
{{- if or (has .Values.teamName $reserved) (hasPrefix "openshift-" .Values.teamName) (hasPrefix "kube-" .Values.teamName) -}}
{{- fail (printf "teamName '%s' collides with a reserved/system namespace" .Values.teamName) -}}
{{- end -}}
{{- end }}

{{/*
ServiceAccount name helper.
*/}}
{{- define "team-onboarding.saName" -}}
{{- .Values.serviceAccount.name | default (printf "%s-deployer" .Values.teamName) -}}
{{- end }}
