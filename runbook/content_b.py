"""Sections 7 to 9: Confluent Cloud, SRS and search cluster, secrets and identity."""
from content_a import GEN, PUB, OWN


def s7_kafka(b):
    b.h1("Externalized Kafka on Confluent Cloud")
    b.h2("What Pega uses Kafka for")
    b.p("Pega uses Kafka in two different ways, and they must not be confused. The first is the stream service: every "
        "queue processor and job scheduler uses it, so Pega is not fully functional without it [R13]. This is what the Helm "
        "stream section configures and what this section designs. The second is the Kafka data set, an optional application "
        "feature used mainly by Pega Customer Decision Hub and Process AI. Pega requires that Kafka data sets use a different "
        "Kafka service from the stream service [R13].")
    b.figure(PUB + "pega_docs_kafka-use-cases.jpg", "The two Kafka use cases in Pega Platform",
             "Source: Pega Documentation, \"External Kafka in your deployment\" [R13]. © Pegasystems Inc. Reproduced with attribution.",
             width_cm=15.5)
    b.h2("Pega requirements mapped to Confluent Cloud")
    b.p("Confluent Cloud is a managed service, so some Kafka broker settings that Pega lists cannot be set by the customer. "
        "The table shows each requirement, how Confluent Cloud handles it, and what this runbook does about it.")
    b.table(["Pega requirement [R13]", "Confluent Cloud position", "Action in this runbook"], [
        ["Kafka version compatible with the Pega client (4.0.0 in '26) [R3]", "Fully managed; Confluent runs current Kafka versions.", "Validate produce, consume and transactions from a Pega pod in every environment (V-K-05)."],
        ["Confluent 5.4.x or later", "Confluent Cloud is a current release line.", "None beyond V-K-05."],
        ["message.max.bytes = 5000000", "Topic max.message.bytes defaults to 2,097,164; editable; maximum 20,971,520 on Dedicated and Enterprise, 8,388,608 on Basic and Standard [R39].", "After each start, check max.message.bytes on every Pega topic and raise it to 5,000,000 where lower (V-K-08). Repeat after Pega creates new topics."],
        ["replica.fetch.max.bytes, replica.fetch.response.max.bytes = 5000100", "Broker replication settings are managed by Confluent and are not in the list of editable cluster settings [R40].", "Logged in Section 23 (RC-04). Confirm with Confluent support that topics at 5,000,000 bytes replicate normally."],
        ["unclean.leader.election.enable = false", "Managed by Confluent; not customer-editable [R40].", "Logged in Section 23 (RC-04). Request written confirmation from Confluent."],
        ["auto.create.topics.enable = false", "Default false on Dedicated; editable [R40].", "Keep false. Pega creates topics through the Kafka AdminClient, which needs the CREATE operation in the topic ACL."],
        ["Generic Kafka security only; no IAM roles", "SASL_SSL with API keys (PLAIN) is generic Kafka.", "Use SASL_SSL with PLAIN (Section 7.5)."],
        ["ACLs for TOPIC, GROUP, TRANSACTIONAL_ID and CLUSTER IDEMPOTENT_WRITE", "Supported through Confluent ACLs on service accounts.", "Create the ACLs in Section 7.5 before the first Pega start."],
        ["Sizing: production 3 brokers, 4 cores, 16 GB, 200 GB; supports about 1000 partitions", "Capacity is bought in eCKU or CKU; partition limits per unit are published [R37].", "Size by partition count and throughput measured in rehearsal (Section 7.6)."],
    ], caption="Pega Kafka requirements mapped to Confluent Cloud", widths=[4.5, 5.6, 6.5], size=8.5)
    b.h2("Cluster type")
    b.p("Confluent offers Basic, Standard, Enterprise, Dedicated and Freight clusters [R37]. Basic and Standard are fine for "
        "short-lived development work but do not offer private networking. Freight does not support idempotent producers or "
        "transactions [R37], and Pega needs both: its ACL profile asks for IDEMPOTENT_WRITE and TRANSACTIONAL_ID permissions "
        "[R13]. That leaves Enterprise and Dedicated for any environment that holds real data.")
    b.table(["Dimension (per unit)", "Basic eCKU", "Standard eCKU", "Enterprise eCKU", "Dedicated CKU"], [
        ["Ingress MBps", "5", "25", "60", "60"],
        ["Egress MBps", "15", "75", "180", "180"],
        ["Partitions (before replication)", "30", "250", "3,000", "4,500"],
        ["Private networking", "No", "No", "Yes (Private Link)", "Yes (Private Link or VNet peering)"],
        ["Fit for Pega production", "No", "No", "Yes", "Yes"],
    ], widths=[4.6, 2.6, 2.6, 3.2, 3.6], caption="Confluent Cloud cluster limits relevant to Pega (source [R37])", size=9, label="confluent_limits")
    b.callout("caution", "Enterprise clusters that use Private Link on Azure are limited to 32 eCKU [R37]. Count the partitions for every environment that will share a cluster, including the about 100 extra partitions that Hazelcast removal adds per environment [R6], before choosing Enterprise.")
    b.figure(GEN + "fig_decision_confluent.png", "Decision: Confluent Cloud cluster type", OWN, width_cm=12.5)
    b.h2("Private networking")
    b.p("Azure Private Link gives one-way private access from the customer VNet to Confluent Cloud. Confluent publishes the "
        "Azure set-up for Dedicated clusters: create or identify a Confluent network, add a Private Link access, create one "
        "private endpoint per zone in the customer subscription, set up DNS records, and validate connectivity [R38]. "
        "Enterprise clusters use Confluent's Private Link for serverless products, which follows the same customer-side pattern "
        "of private endpoints and DNS.")
    b.figure(PUB + "confluent_azure_privatelink.png", "Azure Private Link between a customer VNet and Confluent Cloud",
             "Source: Confluent Documentation, \"Use Azure Private Link for Dedicated clusters on Confluent Cloud\" [R38]. © Confluent, Inc. Reproduced with attribution.",
             width_cm=12)
    b.figure(PUB + "confluent_azure_dns_records.png", "DNS records that Confluent lists for Azure Private Link",
             "Source: Confluent Documentation [R38]. © Confluent, Inc. Reproduced with attribution.", width_cm=15.5)
    b.table(["Step", "Action", "Evidence to keep"], [
        ["N-1", "Create the Confluent network in the same Azure region as AKS and register the customer subscription for Private Link.", "Confluent network ID; subscription ID registered."],
        ["N-2", "Create one private endpoint per zone in the private endpoint subnet, using the service aliases shown by Confluent.", "Endpoint names, private IPs, connection state Approved."],
        ["N-3", "Create the private DNS zone for the Confluent DNS domain and the wildcard and zonal records shown by Confluent. Link it to the spoke VNet or the hub resolver.", "Zone records export."],
        ["N-4", "From a pod in the Pega namespace, resolve the bootstrap name and a broker name; both must return private IPs.", "nslookup output (Appendix D, command K-1)."],
        ["N-5", "From the same pod, open TLS to the bootstrap name on port 9092.", "openssl s_client output showing the certificate chain (K-2)."],
        ["N-6", "Run a metadata request and confirm every broker name resolves privately.", "kcat -L output (K-3)."],
    ], caption="Private Link setup steps", widths=[1.4, 9.4, 5.8], size=9)
    b.callout("note", "Confluent states that the Confluent CLI and Schema Registry access might need internet connectivity even when the cluster uses Private Link [R38]. Allow the Confluent control plane through the firewall for the administration jump host only, not for Pega pods.")
    b.h2("Security: authentication and ACLs")
    b.h3("Authentication choice")
    b.p("Pega lists four SASL options [R13], but the Helm chart's saslMechanism parameter accepts PLAIN, SCRAM-SHA-256 and "
        "SCRAM-SHA-512 [R28]. Confluent Cloud API keys use SASL/PLAIN. OAUTHBEARER has its own Pega article, but this design "
        "uses it only after it has been proven with Confluent in a rehearsal ({ref:fig_kafka_auth}).")
    b.figure(GEN + "fig_decision_kafka_auth.png", "Decision: Pega to Kafka authentication", OWN, width_cm=11, label="kafka_auth")
    b.h3("Service account and ACLs")
    b.p("Create one Confluent service account per Pega environment. Grant it only the ACLs Pega lists, scoped to that "
        "environment's topic prefix. With streamNamePattern `pega-<env>-{stream.name}`, the prefix is `pega-<env>-`.")
    b.table(["Resource type", "Resource name", "Operation", "Pattern", "Why"], [
        ["TOPIC", "`pega-<env>-`", "ALL", "PREFIXED", "Create, write, read and delete Pega topics"],
        ["GROUP", "`pega-<env>-`", "ALL", "PREFIXED", "Consumer groups for queue processors and data flows"],
        ["TRANSACTIONAL_ID", "*", "READ, WRITE", "LITERAL", "Transactional producers"],
        ["CLUSTER", "the cluster", "IDEMPOTENT_WRITE", "LITERAL", "Idempotent producers"],
    ], widths=[3, 3, 2.6, 2.3, 5.7], caption="Kafka ACLs for the Pega service account (source [R13])", size=9, label="acls")
    b.code("""# Example with the Confluent CLI.
# Check flag names with: confluent kafka acl create --help
confluent kafka acl create --allow --service-account <sa-id> --operations all \\
  --topic "pega-<env>-" --prefix --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> --operations all \\
  --consumer-group "pega-<env>-" --prefix --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> --operations read,write \\
  --transactional-id "*" --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> \\
  --operations idempotent-write --cluster-scope --cluster <lkc-id>""", title="Creating the ACLs")
    b.callout("important", "The Hazelcast removal prerequisites name five topics (deployment.registry, NeoRemoteExecutionRequest, NeoRemoteExecutionResponse, SystemPulse_SystemPulseTopicName, Notification_Manager) [R6]. The documentation does not say whether streamNamePattern is applied to them. In the first rehearsal, list the topics Pega creates and confirm every one is covered by the prefixed ACL (V-K-07). If any is not, add a literal ACL for it.")
    b.h2("Topic design and partition budget")
    b.table(["Setting", "Value", "Reason"], [
        ["streamNamePattern", "`pega-<env>-{stream.name}`; a new `<env>` value in Release 2 (for example `prd2`)", "Separates environments on a shared cluster; a new prefix in Release 2 keeps the 8.8 topics untouched for rollback (AD-05). Default is pega-{stream.name} [R28]."],
        ["replicationFactor", "3", "Pega recommended value; cannot exceed the number of brokers [R28]."],
        ["Topic creation", "By Pega through AdminClient (CREATE in ACL)", "Pega says auto.create.topics.enable is a legacy method [R13]. If security policy forbids CREATE, pre-create topics from the rehearsal inventory and the lists in [R3, R6]."],
        ["max.message.bytes", "5,000,000 on every Pega topic", "Matches Pega's maximum message size [R13]; Confluent default is lower [R39]."],
        ["SystemPulse_SystemPulseTopicName", "6 partitions for '26", "Pega '26 prerequisite; automatic if dynamic creation is enabled [R3]."],
    ], caption="Topic design settings", widths=[3.5, 5.5, 7.6], size=9)
    b.p("Partition count drives both Confluent cost and limits. Measure it rather than estimate it:")
    b.steps([
        "After the first full start of each release in staging, count partitions under the environment prefix (Appendix D, command K-5).",
        "Add about 100 partitions per environment for the Hazelcast removal messaging topics if they are not yet present [R6].",
        "During Release 2, the 8.8 prefix and the new prefix exist together. Budget for both until the 8.8 topics are deleted after the rollback window closes.",
        "Compare the total with the per-unit partition limit for the chosen cluster type ({ref:tab_confluent_limits}) and keep at least 30 % headroom for new queue processors.",
    ])
    b.h2("Helm configuration of the stream service")
    b.p("The stream section of the Pega Helm chart connects every tier to Kafka [R14]. Plain-text passwords and the JAAS string are "
        "left empty and supplied through an external secret, whose keys must be STREAM_TRUSTSTORE_PASSWORD, "
        "STREAM_KEYSTORE_PASSWORD and STREAM_JAAS_CONFIG [R28].")
    b.code("""stream:
  enabled: true
  bootstrapServer: "<bootstrap-host>:9092"
  securityProtocol: SASL_SSL
  saslMechanism: PLAIN
  trustStore: ""                 # set only if a private CA must be trusted
  keyStore: ""                   # not used with SASL/PLAIN
  jaasConfig: ""                 # supplied by the external secret
  streamNamePattern: "pega-<env>-{stream.name}"
  replicationFactor: "3"
  external_secret_name: "pega-stream-secret"
""", title="values-<env>.yaml: stream section")
    b.code("""org.apache.kafka.common.security.plain.PlainLoginModule required
  username="<api-key>" password="<api-secret>";""",
           title="Value stored in Key Vault for STREAM_JAAS_CONFIG (stored as one line)")
    b.p("If an application needs messages larger than 5,000,000 bytes, Pega requires the JVM arguments "
        "`-Dstream.producer.max.request.size` and `-Dstream.producer.buffer.memory` on every tier [R13]. They are set in "
        "`catalinaOpts` per tier [R28], and the topic max.message.bytes must be raised to match, within the Confluent maximum [R39].")
    b.h2("prpcUtils after Hazelcast removal")
    b.p("From '25, prpcUtils needs its own connection to Kafka for clustering. Pega documents a `-DNodeSettings` argument in "
        "`custom.jvm.args` of prpcUtils.properties, and says this approach applies to '25.x and '26.x [R10]. Use it for any "
        "prpcUtils runs on 26.1.1, for example rule imports in a pipeline.")
    b.code("""custom.jvm.args=-Xmx4g -DNodeSettings=services/stream/provider=ExternalKafka;\\
services/stream/broker/url=<bootstrap-host>:9092;\\
services/stream/encryption/security/protocol=SASL_SSL;\\
services/stream/encryption/sasl/mechanism=PLAIN;\\
services/stream/encryption/sasl/jaas/config=<jaas-from-key-vault>;\\
services/stream/name/pattern=pega-<env>-;\\
services/stream/external/replication/factor=3;\\
dsm/services/stream/clustername=<lkc-id>""", title="prpcUtils.properties (written as one line in the file)")
    b.callout("caution", "This file holds the JAAS secret in plain text. Generate it at run time in the pipeline from Key Vault and delete it after the run. Pega recommends a heap of at least -Xmx4g [R10].")


def s8_search(b):
    b.h1("Externalized search: SRS with Elasticsearch or OpenSearch")
    b.h2("How Pega search works from '24.2")
    b.p("SRS is a Pega backing service that sits between Pega Platform and the search cluster. Pega nodes send indexing "
        "and query requests to SRS, and SRS manages the indexes in Elasticsearch or OpenSearch [R16]. Embedded search and the "
        "legacy external plug-in were deprecated in 8.8 and are not available from '24.2 [R16]. SRS isolates the data of each "
        "Pega environment with a CUSTOMER_DEPLOYMENT_ID that becomes the index prefix [R16, R28].")
    b.figure(PUB + "pega_academy_three_node.png", "Earlier Pega cluster layout with embedded Kafka and in-cluster Elasticsearch",
             "Source: Pega Academy, \"Cloud deployment architecture\" [R36]. © Pegasystems Inc. Reproduced with attribution. Shown for comparison with the 8.8 source; this layout is not supported from '24.2.",
             width_cm=8.5)
    b.figure(PUB + "pega_academy_srs_cloud_deployment.png", "Client-managed cloud deployment overview with SRS as a backing service",
             "Source: Pega Academy, \"Search and Reporting Service\" [R34]. © Pegasystems Inc. Reproduced with attribution. The Hazelcast pod in this illustration does not apply to '25 and later.",
             width_cm=12)
    b.h2("Requirements and supported versions")
    b.table(["SRS image", "Authentication", "Certified search versions ('26 documentation)", "Pega best practice"], [
        ["search-n-reporting-service", "Not enabled", "Elasticsearch 7.17.9, 7.17.29", "Not for production"],
        ["search-n-reporting-service", "Enabled", "Elasticsearch 7.17.9, 7.17.29, 8.10.3, 8.15.1, 8.15.5, 8.18.2, 8.18.3, 8.19.11", "Elasticsearch 8.18.3"],
        ["search-n-reporting-service-os", "Enabled", "AWS OpenSearch service with Elasticsearch 7.10; OpenSearch 1.3, 2.15, 2.19", "OpenSearch 2.15"],
    ], widths=[3.8, 2.4, 7, 3.4], caption="SRS compatibility for Pega 8.6 and later, SRS 1.44.3 or later (source [R16])", size=9)
    b.callout("note", "The Helm chart README lists a newer SRS (1.49.2) and more Elasticsearch versions (up to 8.19.22) than the '26 documentation page. Section 23 (RC-01) records this. This design selects versions that appear in the Pega documentation matrix, and uses the newest SRS image that the Helm README lists for the chart version deployed.")
    b.bullets([
        "Use only official Elasticsearch or OpenSearch images; custom images such as bitnami/elasticsearch are not supported [R16].",
        "Do not share the search cluster with non-Pega software [R16].",
        "The search cluster deployed by the backingservices chart is for development and test only; OpenSearch cannot be used for that option [R16, R29].",
        "SRS supports Pega 8.6 and later, so the same SRS deployment serves 8.8 in Release 1, the bridge release in Release 2 and 26.1.1 in Release 3 [R16].",
    ])
    b.h2("Choosing the search provider")
    b.p("Fixed decision D-08 excludes an Azure-managed Elasticsearch service. Azure does not offer a first-party managed "
        "OpenSearch service either, so the provider is a third party or the customer. Pega accepts open-source, licensed or cloud "
        "subscription options [R16].")
    b.figure(GEN + "fig_decision_search_backend.png", "Decision: search backend for SRS", OWN, width_cm=13)
    b.table(["Option", "SRS image", "Strengths", "Points to validate"], [
        ["Elastic Cloud hosted on Azure", "search-n-reporting-service", "Vendor-managed; Elasticsearch versions on the Pega matrix", "Elastic licence acceptance; private connectivity from the customer VNet; version pinning to a matrix version"],
        ["Managed OpenSearch from a third-party provider running on Azure", "search-n-reporting-service-os", "Apache 2.0 licence; vendor-managed", "Region availability; private connectivity; ability to set action.auto_create_index and action.destructive_requires_name; version 2.15 or 2.19 available"],
        ["Self-managed OpenSearch on a dedicated AKS node pool", "search-n-reporting-service-os", "Full control; no third-party contract", "Customer operates upgrades, backups, scaling and on-call; official images only"],
    ], caption="Search provider options", widths=[3.6, 3.4, 4.2, 5.4], size=8.5)
    b.figure(PUB + "opensearch_cluster.png", "OpenSearch cluster roles: cluster-manager and data nodes",
             "Source: OpenSearch Documentation, \"Creating a cluster\" [R42]. © OpenSearch contributors. Reproduced with attribution.",
             width_cm=8)
    b.h2("Sizing")
    b.p("Pega publishes three sizing examples. Start from the default table for production and adjust after measuring "
        "indexing and query performance, as Pega advises [R16].")
    b.table(["Service", "Landscape", "Instances", "CPU each", "RAM GB each", "Storage GB each"], [
        ["Cluster-manager (master) nodes", "Production, stage", "3", "2", "8", "N/A"],
        ["Data nodes", "Production, stage", "3", "4", "16", "100"],
        ["Data nodes", "Testing, development", "1", "2", "8", "100"],
        ["SRS", "Production, stage", "3 (autoscaled)", "2", "2", "N/A"],
        ["SRS", "Testing, development", "1 (autoscaled)", "2", "2", "N/A"],
    ], widths=[4.4, 3.4, 2.4, 1.8, 2.2, 2.4], caption="Pega default sizing for search and SRS (source [R16])", size=9)
    b.table(["Service", "Landscape", "Instances", "CPU each", "RAM GB each", "Storage GB each"], [
        ["Cluster-manager nodes", "Production, stage", "3", "2", "8", "N/A"],
        ["Data nodes", "Production, stage", "9", "4", "16", "250"],
        ["Data nodes", "Testing, development", "4", "4", "16", "250"],
        ["SRS", "Production, stage", "3 (autoscaled)", "2", "2", "N/A"],
    ], widths=[4.4, 3.4, 2.4, 1.8, 2.2, 2.4], caption="Pega sizing example for about 2 TB of searchable data and about 750,000 documents (source [R16])", size=9)
    b.p("Pega's minimum production sizing is three cluster-manager nodes (2 CPU, 4 GB) and three data nodes (2 CPU, 8 GB, "
        "50 GB) [R16]. Release 2 builds a second set of indexes under a new customerDeploymentId while the 8.8 indexes still exist, "
        "so plan data node storage for two copies of the production indexes until the rollback window closes.")
    b.h2("Search cluster settings")
    b.p("SRS needs two cluster settings. If the SRS user has the manage cluster privilege, SRS disables index auto-creation "
        "itself; otherwise set it manually. Elasticsearch 8 and later also need destructive_requires_name set to false because "
        "SRS deletes indexes with a pattern [R16].")
    b.code("""PUT _cluster/settings
{
  "persistent": {
    "action": {
      "auto_create_index": "false",
      "destructive_requires_name": "false"
    }
  }
}""", title="Cluster settings required by SRS")
    b.callout("caution", "The setting destructive_requires_name false allows index deletion by wildcard for every user with delete rights. Limit index delete privileges to the SRS user, and restrict administrator access to the search cluster to a break-glass group.")
    b.h2("SRS deployment (backingservices chart)")
    b.code("""global:
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
      clientAuthentication: "want"      # "need" enforces mTLS from Pega
      keystore:
        file: "srs-keystore.p12"
        type: "PKCS12"
      truststore:
        file: "srs-truststore.jks"
        type: "JKS"
      certsSecret: "srs-runtime-certs"  # store files and their passwords
  srsStorage:
    provisionInternalESCluster: false
    domain: "<search-host>"
    port: 443
    protocol: https
    tls:
      enabled: true
    # certificateName and certsSecret are set only if the provider uses a private CA
    basicAuthentication:
      enabled: true
    authSecret: "srs-search-credentials" # keys: username, password
    requireInternetAccess: false
    networkPolicy:
      enabled: true""", title="backingservices values-<env>.yaml (OpenSearch example)")
    b.p("The keys come from the SRS chart README [R29]. Use search-n-reporting-service instead of the -os image if the "
        "backend is Elasticsearch. The README also documents mTLS and PKI client-certificate options between SRS and the search "
        "cluster, and make targets (external-es-secrets, update-external-es-secrets, srs-mtls-prerequisite) that create the "
        "certificate secrets [R29].")
    b.h2("Connecting Pega to SRS")
    b.p("The pegasearch section of the Pega Helm chart points Pega at SRS. Remove the legacy parameters (image, memLimit, "
        "replicas) that described the old plug-in [R18].")
    b.code("""global:
  customerDeploymentId: "<env-deployment-id>"   # index prefix; equals the guid claim
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
    external_secret_name: "pega-srs-oauth"       # key: SRS_OAUTH_PRIVATE_KEY
  srsMTLS:
    enabled: false                   # true if SRS requires client certificates
    external_secret_name: """"", title="values-<env>.yaml: Pega to SRS")
    b.h2("Authorization between Pega and SRS")
    b.p("Pega recommends an OAuth service of the customer's choice to authorize Pega to SRS [R16]. Pega obtains a token "
        "with the client credentials grant, using a private key (private_key_jwt) or a client secret (client_secret_basic), "
        "and the scope pega.search:full [R18, R28]. SRS validates the token signature with the public key URL and checks that "
        "the guid claim equals the customerDeploymentId [R28].")
    b.figure(GEN + "fig_srs_auth_flow.png", "Token flow between Pega, the identity provider and SRS", OWN, width_cm=16)
    b.callout("important", ["Open decision OD-16: confirm that the chosen identity provider can issue the claims SRS checks. "
              "For example, Microsoft Entra ID access tokens for the client credentials flow carry application permissions in "
              "the roles claim rather than the scp claim [R45], and do not carry a guid claim by default.",
              "Prove the token in the first non-production environment by decoding it and confirming the scope and guid values "
              "(V-S-06) before any production build depends on it."])
    b.h2("Customer deployment ID")
    b.bullets([
        "Set global.customerDeploymentId explicitly in every environment. If left empty, it defaults to the namespace name [R28].",
        "Treat it as immutable for the life of an environment. Pega asks for an immutable CUSTOMER_DEPLOYMENT_ID when several environments share one SRS [R17].",
        "Use a new value in Release 2 (for example `<env>-r2`) so that the bridge release builds new indexes and the 8.8 indexes remain for rollback (AD-06).",
        "Keep the Release 2 value unchanged in Release 3, so the zero-downtime update keeps the same indexes.",
    ])
    b.h2("Encryption between Pega and SRS")
    b.p("Pega's best practice is to encrypt Pega-to-SRS traffic at the infrastructure layer with a service mesh, or to use "
        "TLS [R16]. This design enables TLS on SRS (srsRuntime.ssl.enabled) and uses the https SRS URL. Setting "
        "clientAuthentication to need enforces mutual TLS, which requires pegasearch.srsMTLS with the Pega keystore and "
        "truststore [R28, R29].")


def s9_secrets(b):
    b.h1("Secrets, certificates and identity")
    b.p("Fixed decision D-09 forbids plain-text secrets in Helm values. The Pega Helm chart supports the External Secrets "
        "Operator for database, registry, stream, SRS and certificate secrets [R28]. Key Vault is the system of record.")
    b.figure(GEN + "fig_secrets_flow.png", "Secret delivery from Key Vault to Pega and SRS pods", OWN, width_cm=16)
    b.table(["Kubernetes secret", "Keys", "Consumed by", "Key Vault secret", "Rotation"], [
        ["pega-db-secret", "DB_USERNAME, DB_PASSWORD (or token-based settings)", "Pega tiers, installer (jdbc.external_secret_name)", "`<env>-pega-db`", "Per database policy"],
        ["pega-stream-secret", "STREAM_TRUSTSTORE_PASSWORD, STREAM_KEYSTORE_PASSWORD, STREAM_JAAS_CONFIG", "Pega tiers (stream.external_secret_name)", "`<env>-confluent-jaas`", "API key rotation, Section 9.1"],
        ["pega-srs-oauth", "SRS_OAUTH_PRIVATE_KEY", "Pega tiers (pegasearch.srsAuth.external_secret_name)", "`<env>-srs-oauth-key`", "Yearly or per IdP policy"],
        ["srs-search-credentials", "username, password", "SRS (srsStorage.authSecret)", "`<env>-search-user`", "Quarterly"],
        ["srs-runtime-certs", "srs-keystore.p12, srs-truststore.jks, keystorePassword, truststorePassword", "SRS (srsRuntime.ssl.certsSecret)", "`<env>-srs-tls`", "Before certificate expiry"],
        ["pega-tier-tls", "TOMCAT_KEYSTORE_CONTENT, TOMCAT_KEYSTORE_PASSWORD, ca.crt", "Web tier TLS (tier.service.tls)", "`<env>-pega-tls`", "Before certificate expiry"],
    ], widths=[3, 4.4, 3.8, 2.8, 2.6], caption="Secret inventory", size=8.5)
    b.p("Key names for the stream and SRS OAuth secrets are fixed by the Pega Helm chart [R28]; key names for the web tier "
        "keystore are also fixed [R28]. The database secret keys follow the chart's jdbc section. Secret names are this "
        "design's convention.")
    b.code("""apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: keyvault
  namespace: pega-<env>
spec:
  provider:
    azurekv:
      authType: WorkloadIdentity
      vaultUrl: "https://<vault-name>.vault.azure.net"
      serviceAccountRef:
        name: eso-keyvault-reader
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pega-stream-secret
  namespace: pega-<env>
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: keyvault
    kind: SecretStore
  target:
    name: pega-stream-secret
  data:
    - secretKey: STREAM_TRUSTSTORE_PASSWORD
      remoteRef: { key: <env>-stream-truststore-password }
    - secretKey: STREAM_KEYSTORE_PASSWORD
      remoteRef: { key: <env>-stream-keystore-password }
    - secretKey: STREAM_JAAS_CONFIG
      remoteRef: { key: <env>-confluent-jaas }""", title="External Secrets Operator objects (Azure Key Vault provider [R47])")
    b.callout("note", "Check the External Secrets Operator API version installed in the cluster (v1beta1 or v1) and use it in these manifests. The truststore and keystore password keys can hold empty values when SASL/PLAIN is used without a private CA, but keep the keys so the order Pega expects is preserved [R28].")
    b.h2("Rotating the Confluent API key")
    b.steps([
        "Create a second API key for the same service account in Confluent Cloud. The ACLs belong to the service account, so they apply to both keys.",
        "Write the new JAAS string to the Key Vault secret `<env>-confluent-jaas` as a new version.",
        "Wait for the External Secrets Operator refresh, or force it by annotating the ExternalSecret. Confirm the Kubernetes secret changed.",
        "Run a rolling restart of the Pega tiers (kubectl rollout restart deployment). Pods read the JAAS value at start.",
        "Confirm the Stream landing page shows Status NORMAL and queue processors are processing.",
        "Delete the old API key in Confluent Cloud. Record the change in the operations log.",
    ])
    b.h2("Certificates")
    b.table(["Certificate", "Issued by", "Used for", "Renewal owner"], [
        ["Public TLS certificate for the Pega host name", "Customer public CA", "Application Gateway listener", "Platform team"],
        ["Web tier backend certificate", "Customer private CA", "Application Gateway to web pods", "Platform team"],
        ["SRS server certificate", "Customer private CA", "Pega to SRS TLS", "Platform team"],
        ["Confluent broker certificates", "Confluent (public CA)", "SASL_SSL from Pega", "Confluent"],
        ["Search service certificate", "Provider or customer CA", "SRS to search cluster TLS", "Search provider"],
    ], caption="Certificates", widths=[5, 3.6, 4.4, 3.6], size=9)
    b.callout("caution", "Do not route Pega-to-Confluent or SRS-to-search traffic through a TLS-inspecting proxy. Re-signed certificates break the trust chain the clients check. Private endpoint traffic stays inside the VNet and does not need inspection.")
