"""Helm values files for the pega and backingservices charts (chart 4.13.0), generated per environment and run."""
import envs as E

SIZES = {
    # code: (web replicas, web max, batch replicas, batch max, srs replicas)
    "dev": (1, 2, 1, 2, 1),
    "sit": (1, 3, 1, 3, 1),
    "uat": (2, 3, 1, 3, 1),
    "perf": (3, 6, 3, 6, 3),
    "ppd": (3, 6, 3, 6, 3),
    "prd": (3, 6, 3, 6, 3),
}

RUNS = {
    "upgrade": "Upgrade run: installer job only, no Pega pods",
    "first": "First-start run: web tier only, batch tier held at zero",
    "deploy": "Steady-state deploy run",
}


def pega_values(code, run):
    web, web_max, bat, bat_max, _ = SIZES[code]
    action = "upgrade" if run == "upgrade" else "deploy"
    if run == "first":
        batch_scale = """      replicas: 0
      hpa:
        enabled: false"""
    else:
        batch_scale = f"""      replicas: {bat}
      hpa:
        enabled: true
        minReplicas: {bat}
        maxReplicas: {bat_max}"""
    return f'''global:
  provider: "aks"
  deployment:
    name: "pega"
  actions:
    execute: "{action}"
  customerDeploymentId: "{E.deployment_id(code)}"
  jdbc:
    url: "<jdbc-url>"
    driverClass: "<jdbc-driver-class>"
    dbType: "<db-type>"
    driverUri: "<driver-uri>"
    external_secret_name: "pega-db-secret"
    rulesSchema: "<rules-schema>"
    dataSchema: "<data-schema>"
  docker:
    registry:
      url: "<acr-name>.azurecr.io"
    imagePullSecretNames: []
    pega:
      image: "<acr-name>.azurecr.io/platform/pega:26.1.1"
  tier:
    - name: "web"
      nodeType: "WebUser"
      replicas: {web}
      service:
        port: 80
        targetPort: 8080
        tls:
          enabled: true
          external_secret_names: ["pega-tier-tls"]
          port: 443
          targetPort: 8443
      ingress:
        enabled: true
        domain: "<pega-host>"
        annotations:
          appgw.ingress.kubernetes.io/request-timeout: "<seconds>"
        tls:
          enabled: true
      resources:
        requests:
          memory: "12Gi"
          cpu: 3
        limits:
          memory: "12Gi"
          cpu: 4
      hpa:
        enabled: true
        minReplicas: {web}
        maxReplicas: {web_max}
      pdb:
        enabled: true
        minAvailable: 1
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: pega-web
    - name: "batch"
      nodeType: "BackgroundProcessing,Search,Batch,RealTime,\\
        Custom1,Custom2,Custom3,Custom4,Custom5,BIX"
{batch_scale}
      resources:
        requests:
          memory: "12Gi"
          cpu: 3
        limits:
          memory: "12Gi"
          cpu: 4
      pdb:
        enabled: true
        minAvailable: 1
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: pega-batch
cassandra:
  enabled: false
hazelcast:
  enabled: false
  clusteringServiceEnabled: false
stream:
  enabled: true
  bootstrapServer: "<bootstrap-host>:9092"
  securityProtocol: SASL_SSL
  saslMechanism: PLAIN
  trustStore: ""
  keyStore: ""
  jaasConfig: ""
  streamNamePattern: "{E.pattern(code)}"
  replicationFactor: "3"
  external_secret_name: "pega-stream-secret"
pegasearch:
  externalSearchService: true
  externalURL: "https://srs-{code}.srs-{code}.svc.cluster.local:8443"
  srsAuth:
    enabled: true
    url: "https://<okta-domain>/oauth2/<auth-server-id>/v1/token"
    clientId: "<okta-client-id>"
    scopes: "pega.search:full"
    authType: "private_key_jwt"
    privateKeyAlgorithm: "RS256"
    external_secret_name: "pega-srs-oauth"
  srsMTLS:
    enabled: false
installer:
  image: "<acr-name>.azurecr.io/platform/installer:26.1.1"
  upgrade:
    upgradeType: "in-place"
    targetRulesSchema: ""
    targetDataSchema: ""
'''


def srs_values(code):
    srs = SIZES[code][4]
    return f'''global:
  k8sProvider: "aks"
  imageCredentials:
    registry: "<acr-name>.azurecr.io"
srs:
  enabled: true
  deploymentName: "srs-{code}"
  srsRuntime:
    replicaCount: {srs}
    srsImage: "<acr-name>.azurecr.io/platform-services/search-n-reporting-service-os:<tag>"
    resources:
      requests:
        cpu: 650m
        memory: "4Gi"
      limits:
        cpu: 1300m
        memory: "4Gi"
    affinity:
      podAntiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              topologyKey: topology.kubernetes.io/zone
              labelSelector:
                matchLabels:
                  app.kubernetes.io/name: srs-service
    env:
      AuthEnabled: true
      OAuthPublicKeyURL: "<okta-jwks-url>"
    ssl:
      enabled: true
      clientAuthentication: "want"
      keystore:
        file: "srs-keystore.p12"
        type: "PKCS12"
      truststore:
        file: "srs-truststore.jks"
        type: "JKS"
      certsSecret: "srs-runtime-certs"
  srsStorage:
    provisionInternalESCluster: false
    domain: "<search-host>"
    port: 443
    protocol: https
    tls:
      enabled: false
    basicAuthentication:
      enabled: true
    authSecret: "srs-search-credentials"
    requireInternetAccess: false
    networkPolicy:
      enabled: false
'''


def srs_netpol(code):
    return f'''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: srs-{code}-default-deny
  namespace: srs-{code}
spec:
  podSelector: {{}}
  policyTypes: ["Ingress", "Egress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: srs-{code}-allow
  namespace: srs-{code}
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: srs-service
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: pega-{code}
      ports:
        - protocol: TCP
          port: 8443
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    - to:
        - ipBlock:
            cidr: "<opensearch-private-endpoint-cidr>"
      ports:
        - protocol: TCP
          port: 443
    - to:
        - ipBlock:
            cidr: "0.0.0.0/0"
            except: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
      ports:
        - protocol: TCP
          port: 443
'''


def all_files():
    out = {}
    for code in ("sit", "prd"):
        for run in RUNS:
            out[f"pega-{code}-{run}.yaml"] = pega_values(code, run)
        out[f"backingservices-{code}.yaml"] = srs_values(code)
        out[f"netpol-srs-{code}.yaml"] = srs_netpol(code)
    return out
