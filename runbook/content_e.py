"""Appendices A to G."""
from docx.shared import Pt

from docx_lib import add_hyperlink, GREY


def app_a_inventory(b):
    b.h1("Configuration inventory", appendix="A")
    b.p("Record every environment-specific value here before deployment and keep this appendix under change control. "
        "The proposed values follow the naming convention used in this document; replace them only through the change process. "
        "Environment codes used below: `dev`, `tst`, `stg`, `prd`.")
    b.h2("Kafka and stream service")
    b.table(["Parameter", "Where set", "Proposed value", "Recorded value and date"], [
        ["Confluent environment and cluster ID", "Confluent Cloud", "One cluster for non-production, one for production (OD-05)", ""],
        ["Bootstrap server", "stream.bootstrapServer; 8.8 stream settings in Release 1", "`<bootstrap-host>:9092` from the cluster settings page", ""],
        ["Network connection", "Confluent network and Azure private endpoint", "Private Link (AD-07)", ""],
        ["Service account", "Confluent Cloud", "`sa-pega-<env>`, one per environment", ""],
        ["API key ID (not the secret)", "Key Vault secret `<env>-confluent-jaas`", "Key ID only in this table", ""],
        ["Topic prefix, Release 1", "streamNamePattern", "`pega-<env>-{stream.name}`", ""],
        ["Topic prefix, Releases 2 and 3", "stream.streamNamePattern", "`pega-<env>2-{stream.name}`", ""],
        ["ACL prefixes", "Confluent ACLs", "Topic and group ACLs for both prefixes while both are in use", ""],
        ["Replication factor", "stream.replicationFactor", "3", ""],
        ["max.message.bytes", "Topic configuration", "5000000", ""],
        ["Partition budget", "Calculation (Section 7.6)", "Measured count under each prefix plus about 100 for Hazelcast removal topics, plus 30 % headroom", ""],
    ], widths=[4.2, 4.4, 4.6, 3.4], caption="Kafka inventory values", size=8.5)
    b.h2("Search and SRS")
    b.table(["Parameter", "Where set", "Proposed value", "Recorded value and date"], [
        ["Search provider and version", "Provider contract", "A version on the SRS matrix (Section 8.2), for example OpenSearch 2.19 or Elasticsearch 8.18.3", ""],
        ["Search endpoint", "srs.srsStorage.domain, port, protocol", "`<search-host>`, 443, https", ""],
        ["SRS user", "Search cluster security", "`srs-<env>` with the manage cluster privilege, or settings applied manually", ""],
        ["SRS image and tag", "srs.srsRuntime.srsImage", "search-n-reporting-service-os or search-n-reporting-service, tag from the chart README", ""],
        ["SRS replicas", "srs.srsRuntime.replicaCount", "3 in production", ""],
        ["customerDeploymentId, Release 1", "SRS connection on 8.8", "`<env>`", ""],
        ["customerDeploymentId, Releases 2 and 3", "global.customerDeploymentId", "`<env>-r2`", ""],
        ["OAuth token endpoint and JWKS URL", "pegasearch.srsAuth.url; srsRuntime.env.OAuthPublicKeyURL", "From the identity provider (OD-16)", ""],
        ["OAuth client ID", "pegasearch.srsAuth.clientId", "One client per environment", ""],
        ["Search snapshot repository", "Search provider", "Provider-managed snapshots, retention per backup policy", ""],
    ], widths=[4.2, 4.4, 4.6, 3.4], caption="Search inventory values", size=8.5)
    b.h2("Pega, AKS and Azure")
    b.table(["Parameter", "Where set", "Proposed value", "Recorded value and date"], [
        ["8.8 exact patch", "Source system", "From the assessment (Section 4.1)", ""],
        ["Bridge release patch", "Installer and Pega images", "Latest '24.1 patch, 24.1.4 or later (OD-02)", ""],
        ["Helm chart version", "Pipeline", "The chart release that supports the target Pega version", ""],
        ["Rules and data schema names", "global.jdbc.rulesSchema, dataSchema", "Per DBA convention", ""],
        ["Release 3 target schemas", "installer.upgrade.targetRulesSchema, targetDataSchema", "New rules schema and temporary data schema", ""],
        ["Namespace names", "Kubernetes", "`pega-<env>`, `srs-<env>`, `platform-ops`", ""],
        ["Key Vault name", "Azure", "One vault per environment", ""],
        ["Container registry", "Azure", "One registry; Pega images mirrored and scanned", ""],
        ["Private DNS zones", "Azure", "Zones for Confluent, the search provider, the database, Key Vault and the registry", ""],
        ["Application Gateway request timeout", "Ingress annotation", "Agreed with the application team", ""],
    ], widths=[4.2, 4.4, 4.6, 3.4], caption="Pega and platform inventory values", size=8.5)


def app_b_values(b):
    b.h1("Consolidated Helm values skeletons", appendix="B")
    b.p("These skeletons bring together the sections shown earlier. Key names come from the Pega Helm charts README files "
        "[R28, R29] and the default values files in the same repository. Values in angle brackets come from Appendix A. "
        "Secrets are never written into these files; each `external_secret_name` points to a Kubernetes secret created by the "
        "External Secrets Operator (Section 9). Validate each file with `helm template` before use.")
    b.h2("Pega chart, Release 3 (26.1.1)")
    b.code('''global:
  provider: "aks"
  deployment:
    name: "pega"
  actions:
    execute: "upgrade-deploy"            # "deploy" after the update completes
  customerDeploymentId: "<env>-r2"
  jdbc:
    url: "<jdbc-url>"
    driverClass: "<jdbc-driver-class>"
    dbType: "<db-type>"
    driverUri: "<driver-uri>"
    external_secret_name: "pega-db-secret"   # keys: DB_USERNAME, DB_PASSWORD
    rulesSchema: "<rules-schema>"
    dataSchema: "<data-schema>"
  docker:
    registry:
      url: "<acr-name>.azurecr.io"
    imagePullSecretNames: []           # AKS pulls from ACR with the kubelet identity
    pega:
      image: "<acr-name>.azurecr.io/platform/pega:26.1.1"
  tier:
    - name: "web"
      nodeType: "WebUser"
      service:
        tls:
          enabled: true
          external_secret_names: ["pega-tier-tls"]
      ingress:
        enabled: true
        domain: "<pega-host>"
        annotations:
          appgw.ingress.kubernetes.io/request-timeout: "<seconds>"
      hpa:
        enabled: true
      pdb:
        enabled: true
        minAvailable: 1
    - name: "batch"
      nodeType: "BackgroundProcessing,Search,Batch,RealTime,\\
        Custom1,Custom2,Custom3,Custom4,Custom5,BIX"
      hpa:
        enabled: true
      pdb:
        enabled: true
        minAvailable: 1
hazelcast:
  enabled: false
  clusteringServiceEnabled: false
stream:
  enabled: true
  bootstrapServer: "<bootstrap-host>:9092"
  securityProtocol: SASL_SSL
  saslMechanism: PLAIN
  streamNamePattern: "pega-<env>2-{stream.name}"
  replicationFactor: "3"
  external_secret_name: "pega-stream-secret"
pegasearch:
  externalSearchService: true
  externalURL: "https://srs-<env>.srs-<env>.svc.cluster.local"
  srsAuth:
    enabled: true
    url: "<idp-token-endpoint>"
    clientId: "<srs-client-id>"
    scopes: "pega.search:full"
    authType: "private_key_jwt"
    privateKeyAlgorithm: "RS256"
    external_secret_name: "pega-srs-oauth"
installer:
  image: "<acr-name>.azurecr.io/platform/installer:26.1.1"
  upgrade:
    upgradeType: "zero-downtime"
    targetRulesSchema: "<new-rules-schema>"
    targetDataSchema: "<temp-data-schema>"''', title="values-<env>.yaml (pega chart)")
    b.callout("note", ["The tier list above shows only the keys this runbook changes. Copy the remaining tier keys (replicas, "
              "resources, livenessProbe, deploymentStrategy) from the default values file of the chart version in use, then "
              "apply the sizes from Section 6.",
              "Check the web tier TLS keys (external_secret_names, keystore and certificate options) against the README of the "
              "chart version deployed; they changed across chart releases [R28]."])
    b.h2("Pega chart, Release 2 differences (bridge release)")
    b.table(["Key", "Release 2 value", "Reason"], [
        ["global.actions.execute", "`upgrade-deploy`, with `installer.upgrade.upgradeType: in-place`", "The copied 8.8 database is updated in place in the new environment; the 8.8 source database is not touched [R28]."],
        ["Pega and installer images", "Bridge release tag, for example 24.1.x", "OD-02"],
        ["hazelcast.enabled, clusteringServiceEnabled", "false, false", "Embedded Hazelcast settings; removal through the DSS (Section 10.6.2) [R8, R28]."],
        ["stream.streamNamePattern", "`pega-<env>2-{stream.name}`", "AD-05"],
        ["global.customerDeploymentId", "`<env>-r2`", "AD-06"],
    ], widths=[4.4, 7, 5.2], caption="Release 2 values that differ from Release 3", size=8.5)
    b.h2("Backingservices chart (SRS)")
    b.code('''global:
  k8sProvider: "aks"
  imageCredentials:
    registry: "<acr-name>.azurecr.io"
srs:
  enabled: true
  deploymentName: "srs-<env>"
  srsRuntime:
    replicaCount: 3
    # -os image for OpenSearch; search-n-reporting-service for Elasticsearch
    srsImage: "<acr-name>.azurecr.io/platform-services/search-n-reporting-service-os:<tag>"
    env:
      AuthEnabled: true
      OAuthPublicKeyURL: "<idp-jwks-url>"
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
      enabled: true
    basicAuthentication:
      enabled: true
    authSecret: "srs-search-credentials"
    requireInternetAccess: false
    networkPolicy:
      enabled: true''', title="values-<env>.yaml (backingservices chart)")


def app_c_evidence(b):
    b.h1("Evidence templates", appendix="C")
    b.p("Each release produces an evidence pack. Store it with the change record. The templates below define what each item "
        "contains so that reviewers can compare rehearsal and production results.")
    b.h2("Evidence pack contents")
    b.table(["Item", "Content", "Produced by", "Used for"], [
        ["E-01 Values diff", "Diff of Helm values against the previous release, secrets excluded", "Platform team", "Change approval"],
        ["E-02 Kafka connectivity", "Output of commands K-1 to K-3 from a pod in the Pega namespace", "Kafka engineer", "V-K-01"],
        ["E-03 ACL export", "Output of the ACL list for the service account", "Kafka engineer", "V-K-02"],
        ["E-04 Drain record", "GET responses of the Stream Migration activity until COMPLETED, with timestamps", "Pega LSA", "V-K-04"],
        ["E-05 Stream status", "Screenshot of the Stream landing page: Provider ExternalKafka, Status NORMAL", "Pega LSA", "V-K-06"],
        ["E-06 Topic list", "Output of K-4 and K-5 for each prefix", "Kafka engineer", "V-K-07, partition budget"],
        ["E-07 Search connectivity", "Output of S-1 to S-3", "Search engineer", "V-S-01, V-S-02"],
        ["E-08 Token check", "Decoded token claims (header and payload only)", "Security architect", "V-S-06"],
        ["E-09 Index status", "Screenshot of the search landing page and output of S-4", "Pega LSA", "V-S-08 to V-S-10"],
        ["E-10 Hazelcast checks", "hazelcast/disabled and checkRemoteExecutionConnectivity results", "Pega LSA", "H-6, H-7"],
        ["E-11 Test report", "Smoke and regression results", "Test lead", "Go/No-Go"],
        ["E-12 Timings", "Start and end time of each step in the release sequence", "Release manager", "Window planning"],
    ], widths=[3.4, 6.8, 2.8, 3.6], caption="Evidence pack items", size=8.5)
    b.h2("Validation record")
    b.table(["Field", "Entry"], [
        ["Check ID", "For example V-K-06"],
        ["Environment and release", "For example stg, Release 2 rehearsal 1"],
        ["Executed by and date", ""],
        ["Command or screen", ""],
        ["Expected result", "Copied from the validation matrix"],
        ["Actual result", ""],
        ["Result", "Pass, Fail, Pass with note"],
        ["Evidence reference", "Evidence pack item number"],
        ["Deviation and action", "Required if the result is not Pass"],
    ], widths=[4.5, 12.1], caption="Validation record template", size=9, first_col_bold=True, zebra=False)
    b.h2("Go/No-Go record")
    b.table(["Gate", "Criteria met", "Evidence", "Decision owner", "Decision and time"], [
        ["Gate 1: readiness", "", "", "Release manager", ""],
        ["Gate 2: services verified", "", "", "Platform lead", ""],
        ["Gate 3: update complete", "", "", "Pega LSA", ""],
        ["Gate 4: business acceptance", "", "", "Business owner", ""],
    ], widths=[3.6, 3.6, 3, 3, 3.4], caption="Go/No-Go record template", size=9, zebra=False)


def app_d_commands(b):
    b.h1("Command reference", appendix="D")
    b.p("Run these commands from a tooling pod in the Pega namespace, so they use the same network path, DNS and egress rules "
        "as Pega. Use an image mirrored into the customer registry. Read secrets from Key Vault at run time and do not leave them "
        "in shell history. Check option names against the installed tool version before use.")
    b.h2("Kafka and Confluent Cloud")
    b.code('''# K-1 DNS: the bootstrap host must resolve to a private IP
nslookup <bootstrap-host>

# K-2 TLS: certificate chain and protocol
openssl s_client -connect <bootstrap-host>:9092 -servername <bootstrap-host> </dev/null

# K-3 Authentication and metadata (kcat)
kcat -b <bootstrap-host>:9092 -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \\
  -X sasl.username="$API_KEY" -X sasl.password="$API_SECRET" -L

# K-4 Topics under a prefix (Confluent CLI)
confluent kafka topic list --cluster <lkc-id> | grep "pega-<env>2-"

# K-5 Partition count under a prefix
kcat -b <bootstrap-host>:9092 -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \\
  -X sasl.username="$API_KEY" -X sasl.password="$API_SECRET" -L -J \\
  | jq --arg p "pega-<env>2-" \\
    '[.topics[] | select(.topic | startswith($p)) | .partitions | length] | add'

# K-6 Topic configuration
confluent kafka topic describe <topic> --cluster <lkc-id>
confluent kafka topic update <topic> --config max.message.bytes=5000000 \\
  --cluster <lkc-id>

# K-7 ACLs for the service account
confluent kafka acl list --service-account <sa-id> --cluster <lkc-id>''', title="Kafka commands")
    b.h2("Pega stream migration")
    b.p("Pega documents these requests against a local Pega instance [R15]. Send them from inside the Pega pod (for example "
        "with kubectl exec) or adjust the host to reach one node. Authenticate as the Pega documentation describes for the "
        "release in use.")
    b.code('''# Start the drain
curl --request POST \\
  http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration
# Check status. The drain is complete when queueSize is 0, timeToDrainMS is 0
# and migrationStatus is COMPLETED
curl --request GET \\
  http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration
# Restart Kafka queues (only when switching between two external Kafka providers)
curl --request DELETE \\
  http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration''',
           title="Stream Migration activity [R15]")
    b.h2("Search and SRS")
    b.code('''# S-1 Version of the search cluster
curl -s -u "$SRS_USER:$SRS_PASSWORD" https://<search-host>/

# S-2 Cluster health
curl -s -u "$SRS_USER:$SRS_PASSWORD" "https://<search-host>/_cluster/health?pretty"

# S-3 Settings required by SRS
curl -s -u "$SRS_USER:$SRS_PASSWORD" "https://<search-host>/_cluster/settings?pretty"

# S-4 Indexes under a customerDeploymentId prefix
curl -s -u "$SRS_USER:$SRS_PASSWORD" \\
  "https://<search-host>/_cat/indices/<deployment-id>*?v"

# S-5 TLS to SRS from the Pega namespace
openssl s_client -connect srs-<env>.srs-<env>.svc.cluster.local:<srs-port> </dev/null''', title="Search commands")
    b.h2("Kubernetes")
    b.code('''# P-1 Pod status
kubectl get pods -n pega-<env> -o wide

# P-2 Pod logs (stream and search errors)
kubectl logs -n pega-<env> <pod> --since=30m | grep -Ei "stream|kafka|srs|search"

# P-3 Rolling restart of a tier
kubectl rollout restart deployment/<tier-deployment> -n pega-<env>
kubectl rollout status deployment/<tier-deployment> -n pega-<env>

# P-4 External secret synchronization
kubectl get externalsecret -n pega-<env>
kubectl describe externalsecret pega-stream-secret -n pega-<env>

# P-5 Installer job logs
kubectl get jobs -n pega-<env>
kubectl logs -n pega-<env> job/<installer-job> -f''', title="Kubernetes commands")
    b.h2("Token inspection")
    b.code('''# Decode the JWT payload without verifying it.
# Do not paste production tokens into web tools.
python3 - "$TOKEN" <<'EOF'
import base64, json, sys
payload = sys.argv[1].split(".")[1]
payload += "=" * (-len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2))
EOF''',
           title="Decode token claims for V-S-06")
    b.h2("Hazelcast removal checks")
    b.p("These checks run from Dev Studio, not from the command line. Open Records > Integration-Resources > Service Package, "
        "open HazelcastDecommission, and in the Methods section run the hazelcast/disabled resource with the GET method and the "
        "current requestor context. The expected answer is true. Then run checkRemoteExecutionConnectivity from the same "
        "package and confirm that all nodes are reachable [R8].")


GLOSSARY = [
    ("ACL", "Access control list. In Kafka, a rule that allows a principal an operation on a resource such as a topic or consumer group."),
    ("AKS", "Azure Kubernetes Service."),
    ("Bridge release", "The intermediate Pega release (latest '24.1 patch) used to remove Hazelcast before the update to 26.1.1."),
    ("CKU, eCKU", "Confluent Unit for Kafka, the capacity unit of Dedicated clusters; elastic CKU for Enterprise clusters."),
    ("CodeSet", "A Pega rule that groups Java libraries imported into Pega Platform."),
    ("customerDeploymentId", "The ID that SRS uses to separate the data of each Pega environment. It becomes the index prefix."),
    ("Data set (Kafka)", "A Pega rule that reads from or writes to a Kafka topic for an application integration. It is separate from the stream service."),
    ("DSS", "Dynamic System Setting, a Pega configuration record."),
    ("External Secrets Operator", "A Kubernetes operator that copies secrets from an external store such as Azure Key Vault into Kubernetes secrets."),
    ("Hazelcast", "The in-memory clustering library used by Pega Platform up to '24.2, removed in '25."),
    ("Helm", "The package manager for Kubernetes used to deploy the Pega charts."),
    ("Jakarta EE", "The successor to Java EE. Tomcat 10.1 uses jakarta.* package names instead of javax.*."),
    ("JAAS", "Java Authentication and Authorization Service. The Kafka client reads its SASL credentials from a JAAS configuration string."),
    ("JWKS", "JSON Web Key Set, the published public keys that SRS uses to check token signatures."),
    ("Private Link", "Azure service that exposes a service through a private IP in the customer VNet."),
    ("Queue processor", "A Pega rule that processes queued items asynchronously through the stream service."),
    ("SASL_SSL", "Kafka security protocol that combines TLS encryption with SASL authentication."),
    ("SRS", "Search and Reporting Service, the Pega backing service between Pega Platform and the search cluster."),
    ("Stream service", "The Pega service that uses Kafka for queue processors, job schedulers and data flows."),
    ("streamNamePattern", "Helm setting that defines how Pega names its Kafka topics; it carries the environment prefix."),
    ("Zero-downtime update", "Pega update type that moves rules into a new schema and performs a rolling reboot, so users keep working during the update."),
]


def app_e_glossary(b):
    b.h1("Glossary", appendix="E")
    b.table(["Term", "Meaning"], [[t, m] for t, m in GLOSSARY], widths=[3.8, 12.8], caption="Glossary of terms", size=9, first_col_bold=True)


def app_f_references(b):
    b.h1("References", appendix="F")
    b.p("Sources were read on the evidence cut-off date in the document control table. Vendor pages change; check each "
        "linked page before a release.")
    for key in sorted(b.refs, key=lambda k: int(k[1:])):
        publisher, title, url = b.refs[key]
        para = b.doc.add_paragraph()
        para.paragraph_format.space_after = Pt(4)
        para.paragraph_format.left_indent = Pt(34)
        para.paragraph_format.first_line_indent = Pt(-34)
        r = para.add_run(f"[{key}]\t")
        r.bold = True
        r.font.size = Pt(9.5)
        r = para.add_run(f"{publisher}. {title}. ")
        r.font.size = Pt(9.5)
        add_hyperlink(para, url, url, size=8.5)


IMAGE_SOURCES = [
    ("pega_docs_pega-platform-architecture.png", "Pega Documentation", "R23"),
    ("pega_academy_external_services.png", "Pega Academy", "R35"),
    ("pega_docs_kafka-use-cases.jpg", "Pega Documentation", "R13"),
    ("confluent_azure_privatelink.png", "Confluent Documentation", "R38"),
    ("confluent_azure_dns_records.png", "Confluent Documentation", "R38"),
    ("pega_academy_three_node.png", "Pega Academy", "R36"),
    ("pega_academy_srs_cloud_deployment.png", "Pega Academy", "R34"),
    ("opensearch_cluster.png", "OpenSearch Documentation", "R42"),
    ("ZDT schema images (five, combined)", "Pega Helm charts, GitHub (Apache License 2.0)", "R33"),
    ("pega_docs_stream-migration-external-kafka-status.png", "Pega Documentation", "R15"),
]


def app_g_images(b):
    b.h1("Image sources and attribution", appendix="G")
    b.p("Figures marked \"Prepared for this implementation\" were drawn for this document from the facts cited in the "
        "surrounding text. The other figures are reproduced from the public sources below, unchanged except for scaling, and "
        "the combination and numbering of the five zero-downtime schema images.")
    b.table(["Image", "Publisher", "Source page"], [[f, p, f"[{r}]"] for f, p, r in IMAGE_SOURCES],
            widths=[7.6, 6, 3], caption="Third-party images", size=9)
    b.callout("important", "Pega, Pega Academy, Confluent and OpenSearch content is subject to the publishers' terms of use. "
              "Before this document is distributed outside the customer and implementation teams, confirm that reuse of these "
              "images is permitted, or replace them with links to the source pages.")


def appendices(b):
    app_a_inventory(b)
    app_b_values(b)
    app_c_evidence(b)
    app_d_commands(b)
    app_e_glossary(b)
    app_f_references(b)
    app_g_images(b)
