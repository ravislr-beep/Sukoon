"""Sections 7 and 8: managed OpenSearch, SRS and Okta; secrets and certificates."""
from content_a import GEN, PUB, OWN
import envs as E
import values_gen as V


def s7_search(b):
    b.h1("Managed OpenSearch and SRS design and configuration")
    b.h2("How search works in 26.1.1")
    b.p("SRS is a Pega backing service between Pega Platform and the search cluster. Pega sends indexing and query requests to "
        "SRS, and SRS manages the indexes in OpenSearch [R14]. SRS isolates each Pega environment's data with a "
        "customerDeploymentId, which becomes the index prefix [R14, R23]. The search service can serve several Pega "
        "deployments, but Pega advises against sharing it with non-Pega software [R14].")
    b.figure(PUB + "pega_academy_srs_cloud_deployment.png", "Client-managed cloud deployment with SRS as a backing service",
             "Source: Pega Academy, \"Search and Reporting Service\" [R28]. © Pegasystems Inc. Reproduced with attribution. The Hazelcast pod in this illustration does not apply to '25 and later.",
             width_cm=12)
    b.h2("SRS and OpenSearch versions")
    b.table(["SRS image", "Authentication", "Certified OpenSearch versions", "Pega best practice"], [
        ["search-n-reporting-service-os", "Enabled", "AWS OpenSearch service with Elasticsearch 7.10; OpenSearch 1.3, 2.15, 2.19", "OpenSearch 2.15"],
    ], widths=[4.2, 2.4, 6.6, 3.4], caption="SRS compatibility with OpenSearch for Pega 8.6 and later, SRS 1.44.3 or later (source [R14])", size=9)
    b.bullets([
        "Choose OpenSearch 2.15 or 2.19. Version 1.3 is on the matrix but is an older line, and the provider may not offer it.",
        "Use the newest `search-n-reporting-service-os` tag that the SRS chart README lists for chart 4.13.0 [R24]. The README lists a newer SRS than the Pega page (RC-01).",
        "Use only official OpenSearch images if the customer runs OpenSearch itself; custom images are not supported [R14].",
        "The search cluster that the backingservices chart can provision is for development and test only, and cannot be OpenSearch [R14, R24].",
    ])
    b.h2("Provider selection")
    b.p("Azure has no first-party managed OpenSearch service, so the choice is between third-party providers that run "
        "OpenSearch in Azure regions and a self-managed cluster on AKS. Pega accepts a cloud subscription, a licensed product "
        "or open source [R14]. This document names no provider: a provider becomes a candidate only when its own "
        "documentation shows an Azure region and OpenSearch 2.15 or 2.19, and that check is part of the selection.")
    b.figure(GEN + "fig_decision_search_provider.png", "Decision: managed OpenSearch provider", OWN, width_cm=11.5)
    b.p("Score each candidate in {ref:tab_os_score}. A provider that fails a mandatory criterion is rejected whatever its score.")
    b.table(["Criterion", "Type", "Weight", "Provider 1", "Provider 2", "Self-managed on AKS"], [
        ["Azure region same as AKS, shown in provider documentation", "Mandatory", "", "", "", "Yes"],
        ["OpenSearch 2.15 or 2.19 available and pinnable", "Mandatory", "", "", "", "Yes"],
        ["Private endpoint into the customer VNet", "Mandatory", "", "", "", "Yes"],
        ["Customer can set `action.auto_create_index` and `action.destructive_requires_name` [R14]", "Mandatory", "", "", "", "Yes"],
        ["Fine-grained access control with index patterns [R40, R41]", "Mandatory", "", "", "", "Yes"],
        ["Snapshots with customer-chosen retention", "Scored", "15", "", "", ""],
        ["Support terms and response times for PROD", "Scored", "20", "", "", ""],
        ["Metrics export to Azure Monitor", "Scored", "15", "", "", ""],
        ["Version upgrade process and notice", "Scored", "15", "", "", ""],
        ["Operations effort for the customer", "Scored", "20", "", "", ""],
        ["Data residency and certifications", "Scored", "15", "", "", ""],
    ], caption="OpenSearch provider selection worksheet", widths=[6.2, 2, 1.4, 2.3, 2.3, 2.4], size=8.5, label="os_score")
    b.p("Only four values depend on the provider: the endpoint host, the port, the SRS user credentials and the CA certificate. "
        "The Helm values in Appendix B keep those in angle brackets and in Key Vault, so the rest of the design does not change "
        "when OD-03 is decided.")
    b.figure(PUB + "opensearch_cluster.png", "OpenSearch cluster roles: cluster-manager and data nodes",
             "Source: OpenSearch Documentation, \"Creating a cluster\" [R37]. © OpenSearch contributors. Reproduced with attribution.",
             width_cm=8)
    b.h2("Cluster settings and sizing")
    b.p("SRS has its own index naming, so index auto-creation must be off. If the SRS user has the manage cluster privilege, "
        "SRS sets this itself; otherwise apply it manually [R14]. SRS also deletes indexes by pattern, which needs "
        "`destructive_requires_name` set to false [R14]. With an index-scoped SRS user (Section 7.5), apply both settings as "
        "an administrator before SRS starts.")
    b.code("""PUT _cluster/settings
{
  "persistent": {
    "action": {
      "auto_create_index": "false",
      "destructive_requires_name": "false"
    }
  }
}""", title="Cluster settings required by SRS (run once per OpenSearch service)")
    b.callout("caution", "`destructive_requires_name: false` lets any user with delete rights remove indexes by wildcard. On a "
              "shared service, give delete rights only through the per-environment index-scoped roles, and keep administrator "
              "access to a break-glass group.")
    b.p("Pega publishes default sizing for search and SRS. Start from it and adjust after measuring, as Pega advises [R14].")
    b.table(["Service", "Landscape", "Instances", "CPU each", "RAM GB each", "Storage GB each"], [
        ["Cluster-manager nodes", "Production, stage", "3", "2", "8", "N/A"],
        ["Data nodes", "Production, stage", "3", "4", "16", "100"],
        ["Data nodes", "Testing, development", "1", "2", "8", "100"],
        ["SRS", "Production, stage", "3 (autoscaled)", "2", "2", "N/A"],
        ["SRS (chart 4.13.0 defaults, for comparison)", "All", "2 minimum, 3 best practice [R24]", "0.65 request, 1.3 limit", "4", "N/A"],
        ["SRS", "Testing, development", "1 (autoscaled)", "2", "2", "N/A"],
    ], widths=[4.4, 3.4, 2.4, 1.8, 2.2, 2.4], caption="Pega default sizing for search and SRS (source [R14])", size=9)
    b.table(["Service", "Starting size", "Basis", "Adjust when"], [
        ["os-np1 (DEV, SIT, UAT)", "3 cluster-manager, 3 data nodes at the Pega production size", "Three environments' indexes plus one full build at a time; three nodes give zone spread", "Disk above 60 % after all three builds"],
        ["os-np2 (PERF, PREPROD)", "Same as os-prd", "Production-like behaviour for load tests and rehearsals", "Never smaller than os-prd"],
        ["os-prd", "3 cluster-manager, 3 or more data nodes; storage from measured volume", "Pega production sizing, scaled by the searchable data measured in the upgraded clone", "Index build or query latency misses target in PERF"],
    ], caption="Starting sizes per OpenSearch service", widths=[3.6, 4.6, 5, 3.4], size=8.5)
    b.bullets([
        "**Searchable data volume.** Measure it from the first upgraded clone: run the full index build in DEV and record index sizes with `_cat/indices` (command S-4). Scale PROD storage from that, plus growth and one rebuild's working space.",
        "**Shards and replicas.** SRS creates and names the indexes itself [R14]. After the first build, read the shard and replica count of each index with `_cat/indices` and record it in Appendix A. Do not change index settings directly unless Pega Support advises it.",
        "**Shard budget.** Add up the shards of every environment on the service and compare with the provider's per-node shard limit.",
        "**Disk watermarks.** Record the provider's low, high and flood-stage watermark values in Appendix A, and alert before the low watermark is reached (Section 18.5). At the flood stage, indexes become read-only and indexing stops (FS-17).",
    ])
    b.h3("Sizing formulas")
    b.p("Pega does not publish a storage or shard formula for SRS. The formulas below are the general OpenSearch sizing "
        "guidance published for Amazon OpenSearch Service [R54, R55], which applies to any OpenSearch cluster because it rests "
        "on OpenSearch's own overheads. Use them with the measured index sizes from the DEV build. The sizing calculator in "
        "Appendix H applies them.")
    b.table(["Quantity", "Formula", "Notes"], [
        ["Primary data (S)", "Sum of `pri.store.size` for `pega26-<code>*` after a full build (S-4)", "Measured, never estimated from database size. Scale to PROD by the ratio of indexed row counts"],
        ["Minimum storage", "S x (1 + replicas) x 1.45 [R54]", "1.45 covers 10 % indexing overhead, 5 % reserved by the operating system and 20 % free space kept below the watermarks"],
        ["Storage with growth", "Minimum storage x (1 + yearly growth) ^ years planned", "Add the peak seen during a full rebuild in DEV if it is above the steady state"],
        ["Shard size", "10 to 30 GiB per primary shard for search workloads [R55]", "SRS sets shard counts. Record them; raise a Pega Support case before changing index settings"],
        ["Shards per node", "At most 25 shards per GiB of JVM heap [R55]", "Heap is normally half the node memory. Add every environment on a shared service"],
        ["Data nodes", "Largest of: storage / usable disk per node; total shards / shards per node; 3 for zone spread", "Use a multiple of the zone count, so each zone holds a full copy of the data"],
    ], caption="OpenSearch sizing formulas", widths=[3.2, 6.6, 6.8], size=8.5, label="os_formulas")
    b.p("Use at least one replica, three cluster-manager nodes and data nodes in three availability zones, with the provider's "
        "zone awareness setting turned on. With one replica and zone awareness, the loss of one zone leaves a full copy of "
        "every shard, so search stays available while the provider replaces the nodes (FS-15).")
    b.h2("Isolation in the shared OpenSearch services")
    b.p("Each environment has its own customerDeploymentId (Section 2.6). Set it explicitly in every values file, because the "
        "chart defaults it to the namespace name [R23], and treat it as immutable, as Pega asks when several environments "
        "share an SRS [R15]. A cloned environment must never reuse another environment's ID: its index build would overwrite "
        "or mix with the other environment's indexes, and its tokens would carry the other environment's `guid`.")
    b.figure(GEN + "fig_decision_srs.png", "Decision: one SRS per environment or one shared SRS", OWN, width_cm=11)
    b.table(["Aspect", "SRS per environment (recommended)", "One SRS per group"], [
        ["OpenSearch credentials", "One user per environment, index-scoped role", "One user for the whole group"],
        ["Blast radius", "An SRS fault or bad upgrade affects one environment", "Affects every environment in the group"],
        ["Upgrades", "Upgrade SRS per environment, in step with that environment's tests", "One upgrade for all; all environments retest"],
        ["Token key set", "SRS points at that environment's Okta key set", "One key set; every environment's tokens come from the same server"],
        ["Cost", "Small: 2 pods in DEV, SIT, UAT (chart minimum [R24]); 3 in PERF, PREPROD, PROD [R14, R24]", "Slightly smaller"],
    ], caption="SRS per environment compared with a shared SRS", widths=[3.4, 6.6, 6.6], size=9)
    b.p("Give each SRS its own OpenSearch user, mapped to a role limited to its index pattern [R40, R41]. Pega says the manage "
        "cluster privilege is optional when the cluster settings are applied manually [R14]. Pega does not say whether SRS "
        "needs any other cluster-level permission, so test the role in DEV (IT-06) and widen it only by the permissions the "
        "SRS log shows as missing.")
    b.code("""pega26-<code>-srs:
  cluster_permissions:
    - cluster_composite_ops
  index_permissions:
    - index_patterns:
        - "pega26-<code>*"
      allowed_actions:
        - "<index action group confirmed in DEV, for example indices_all>"
""", title="Index-scoped role for one environment's SRS user (OpenSearch roles.yml format [R40, R41])")
    b.p("When an environment is refreshed or retired, delete its indexes with `DELETE /pega26-<code>*` as the environment's own "
        "SRS user, which cannot touch any other environment's indexes (Sections 19.3 and 19.4).")
    b.h2("Pega-to-SRS tokens with Okta")
    b.p("Pega obtains a token with the OAuth client credentials grant, authenticating with `private_key_jwt` or "
        "`client_secret_basic`, and asks for the scope `pega.search:full` [R16, R23]. SRS checks the token signature with the "
        "key set at `OAuthPublicKeyURL`, and checks that the `guid` claim equals the customerDeploymentId [R23]. "
        "{ref:fig_okta} shows the flow.")
    b.figure(GEN + "fig_okta_token_flow.png", "Token flow between Pega, Okta and SRS", OWN, width_cm=16.5, label="okta")
    b.h3("Why a custom authorization server is required")
    b.p("Okta's org authorization server cannot be customized: its audience, claims, policies and scopes are fixed, and its "
        "tokens are meant for Okta's own APIs [R42]. The client credentials flow has no user, so it cannot use OpenID scopes "
        "and needs a custom scope [R43]. Custom claims can only be added to a custom authorization server [R44]. Pega's scope "
        "and the `guid` claim are both custom, so Okta tokens for SRS must come from a custom authorization server. Custom "
        "authorization servers are part of Okta API Access Management [R42]. Confirm that the customer's Okta licence "
        "includes it, and how many servers it allows, before M2 (OD-05).")
    b.h3("Issuing a different guid per environment")
    b.table(["Option", "How it works", "Strengths", "Weaknesses"], [
        ["1. One authorization server per environment", "Each server has a claim `guid` with a fixed value, for example `\"pega26-sit\"`, included in access tokens", "Simplest claim; full separation of keys and policies", "Six servers; licence may limit the number"],
        ["2. One shared server, claim based on the client", "One claim `guid` whose value is an Okta expression on the requesting app, for example a conditional on `app.clientId` [R46]", "One server for all non-production; fewer objects", "Every non-production client shares a signing key set; must prove that the expression is evaluated for client credentials tokens"],
    ], caption="Options for the guid claim", widths=[3.2, 5.2, 4, 4.2], size=8.5)
    b.p("Okta's expression language exposes `app.id`, `app.clientId` and `app.profile` for custom claims [R46], and supports "
        "conditional expressions of the form `[Condition] ? [Value if TRUE] : [Value if FALSE]` [R46]. An example claim value "
        "for option 2 is shown below. Okta's pages do not state whether app attributes are available when the token is issued "
        "to a client with no user, so option 2 is accepted only after the DEV test.")
    b.code("""app.clientId == "<dev-client-id>"  ? "pega26-dev"  :
app.clientId == "<sit-client-id>"  ? "pega26-sit"  :
app.clientId == "<uat-client-id>"  ? "pega26-uat"  :
app.clientId == "<perf-client-id>" ? "pega26-perf" :
app.clientId == "<ppd-client-id>"  ? "pega26-ppd"  : "none\"""", title="Claim value expression for option 2 (written as one line in Okta)")
    b.callout("decision", ["Recommendation (OD-05): PROD uses its own custom authorization server with a fixed `guid` claim "
              "of `pega26-prd`. The five non-production environments use one shared custom authorization server with the "
              "client-based claim (option 2), if the DEV test proves it. If the test fails, fall back to option 1 for "
              "non-production.",
              "Proof in DEV: request a token for the DEV client, decode it (command O-2), and confirm `scp` contains "
              "`pega.search:full` and `guid` equals `pega26-dev`. Repeat with the SIT client and confirm `pega26-sit`."])
    b.h3("Okta set-up per environment")
    b.steps([
        "In the authorization server, create the scope `pega.search:full` and an access policy with a rule that allows the client credentials grant for the environment's client.",
        "Create the claim `guid` for access tokens (fixed value for option 1, expression for option 2) [R44].",
        "Create one API services application per environment, named `pega-srs-<code>`, with client authentication by public key / private key (`private_key_jwt`) [R45].",
        "Generate an RSA key pair in a controlled workstation or pipeline. Register the public key in the application's key set (JWKS) [R45]. Store the private key, in PKCS8 form encoded with base64 as the chart requires, in Key Vault as `SRS_OAUTH_PRIVATE_KEY` [R23]. Delete local copies.",
        "Record the client ID, the token endpoint and the key set URL in Appendix A.",
    ])
    b.table(["Setting", "Value", "Source"], [
        ["Issuer", "`https://<okta-domain>/oauth2/<auth-server-id>`", "[R42]"],
        ["Token endpoint (`pegasearch.srsAuth.url`)", "`https://<okta-domain>/oauth2/<auth-server-id>/v1/token`", "[R43]"],
        ["Key set URL (`srsRuntime.env.OAuthPublicKeyURL`)", "The `jwks_uri` value from `https://<okta-domain>/oauth2/<auth-server-id>/.well-known/openid-configuration`", "[R42]"],
        ["Client ID (`pegasearch.srsAuth.clientId`)", "Client ID of `pega-srs-<code>`", "[R23]"],
        ["Authentication (`pegasearch.srsAuth.authType`)", "`private_key_jwt`", "[R23, R45]"],
        ["Key algorithm (`pegasearch.srsAuth.privateKeyAlgorithm`)", "`RS256` (chart default)", "[R23]"],
        ["Scope (`pegasearch.srsAuth.scopes`)", "`pega.search:full`", "[R23]"],
    ], caption="Okta values used in the Helm charts", widths=[5.4, 9.2, 2], size=9)
    b.h3("Network path, token lifetime and rotation")
    b.bullets([
        "Pega pods call the Okta token endpoint, and SRS pods fetch the Okta key set. Both go to `<okta-domain>` on port 443 through the hub firewall. Add an FQDN allow rule for `<okta-domain>` from the Pega and SRS subnets only.",
        "Token lifetime is set in the access policy rule of the authorization server [R42]. Use the same lifetime in all environments and record it in Appendix A. Pega requests a new token when needed; measure how often in DEV by counting token requests in the Okta system log.",
        "Pega does not state whether SRS checks the issuer or audience. Test it in DEV with a token from another authorization server (FS-12) and record the result.",
        "Rotate the client key by adding a second public key to the application, updating `SRS_OAUTH_PRIVATE_KEY` in Key Vault, restarting the Pega tiers, checking search, and then removing the old public key. Pega does not state whether its client assertion carries a key ID (`kid`) header; test the rotation in DEV with both public keys registered (FS-34).",
    ])
    b.h3("Okta signing key rotation and rate limits")
    b.bullets([
        "**Signing keys.** Okta rotates the signing keys of an authorization server about four times a year, and clients must look the key up from the key set URL by its `kid` rather than keep a fixed copy [R53]. SRS must therefore read `OAuthPublicKeyURL` dynamically. Prove it in DEV by rotating the authorization server's keys manually, as Okta allows, and checking that search continues without an SRS restart (FS-33). If the test fails, rotation becomes a planned event with an SRS restart, and the authorization server's key rotation mode is set to manual.",
        "**Rate limits.** Okta applies rate limits per org and per endpoint. A request over the limit receives HTTP 429, and Okta writes warning and violation events to the System Log [R52]. All six environments share the customer's Okta org, so every non-production token request draws on the same limit as production. The key set and discovery endpoints are not the concern; the token endpoint is.",
        "Measure token requests per minute per environment in DEV and under load in PERF (from the System Log), then compare the sum across all environments with the org's published limit for the token endpoint. Keep the token lifetime long enough that Pega does not request a token on each call.",
        "Forward Okta System Log rate-limit warnings and violations to the monitoring service (Section 18.5). A warning means another application in the org, or a misbehaving environment, is close to blocking search for every environment.",
    ])
    b.h2("SRS deployment (backingservices chart)")
    b.p("Each environment has its own SRS release in namespace `srs-<code>`. The keys come from the SRS chart README [R24].")
    b.code("""global:
  k8sProvider: "aks"
  imageCredentials:
    registry: "<acr-name>.azurecr.io"
srs:
  enabled: true
  deploymentName: "srs-<code>"
  srsRuntime:
    replicaCount: <2 in DEV, SIT, UAT; 3 in PERF, PREPROD, PROD>
    srsImage: "<acr-name>.azurecr.io/platform-services/search-n-reporting-service-os:<tag>"
    resources:
      requests: { cpu: 1, memory: "4Gi" }
      limits: { cpu: 2, memory: "4Gi" }
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
    port: <search-port>
    protocol: https
    tls:
      enabled: false
    basicAuthentication:
      enabled: true
    authSecret: "srs-search-credentials"
    requireInternetAccess: false
    networkPolicy:
      enabled: false""", title="backingservices values for one environment (complete files in Appendix B)")
    b.h3("Three chart behaviours that break this design if left at the defaults")
    b.p("These were found by rendering the values files with `helm template` against chart 4.13.0, not from the README alone.")
    b.table(["Key", "What the chart does", "Effect", "Setting in this design"], [
        ["`srsStorage.tls.enabled`", "Means TLS certificate authentication to the search service, not encryption [R24]. The chart refuses to render when it is combined with `basicAuthentication.enabled` (\"Only one authentication can be enabled\")", "Helm install fails", "`false`. Encryption comes from `protocol: https`; the SRS user authenticates with basic authentication"],
        ["`pegasearch.externalURL`", "With `srsRuntime.ssl.enabled: true`, the SRS container serves HTTPS on 8443 only, and its probes call `https://localhost:8443/health`. The Service also exposes 8080 and 80, which point at a port that is not listening [R62]", "An HTTPS URL without a port goes to 443, which the Service does not expose; search fails at first start", "`https://srs-<code>.srs-<code>.svc.cluster.local:8443`"],
        ["`srsStorage.networkPolicy.enabled`", "Allows ingress to SRS from `0.0.0.0/0` on 8080 and 8443, and egress only to an in-cluster `elasticsearch-master` on 9200 and DNS [R62]. `requireInternetAccess` only adds a pod label", "SRS cannot reach the external OpenSearch service or the Okta key set; any pod can call SRS", "`false`, replaced by the policy below"],
    ], caption="SRS chart behaviours found by rendering", widths=[3.4, 6.2, 3.6, 3.4], size=8, label="srs_traps")
    b.code(V.srs_netpol("<code>"), title="Network policies for srs-<code>, replacing the chart policy")
    b.p("The policy allows SRS to be called only from `pega-<code>` on 8443, and lets SRS reach DNS, the OpenSearch private "
        "endpoint and public HTTPS. Okta has no fixed address range, so the last rule is limited to public addresses on 443, "
        "and the hub firewall restricts it to `<okta-domain>` by FQDN. Kubernetes network policies are enforced only if the "
        "AKS cluster was created with a network policy engine; check this before relying on them.")
    b.h2("Index build planning")
    b.p("After Pega connects to SRS, SRS indexes all searchable data, and Pega states that this needs a downtime period. The "
        "length depends on the data model, the resources given to Pega and SRS, the number of queue processors and the amount "
        "of searchable data [R15]. For a cloned environment, the build runs during the first start with intake held "
        "(Section 10.4), so its length sets part of the production outage.")
    b.steps([
        "In every rehearsal, record the start and end of the build, the number of batch pods, SRS replicas and OpenSearch data nodes, and the row counts of the main indexed classes.",
        "Plot build time against searchable data volume across DEV, PERF and PREPROD. PREPROD, built from a recent full-size clone on production-like services, is the best predictor.",
        "Estimate production time as the PREPROD time scaled by the ratio of production to PREPROD data volume, plus 25 % contingency. Use the larger of this and the measured PREPROD time if the volumes are close.",
        "If the estimate does not fit the outage window, add batch pods and OpenSearch data nodes for the cutover and measure again.",
    ])
    b.p("The build is complete when the search landing page shows every class indexed with no errors [R19], the document count "
        "of each main index matches the row count of its class in the database within the tolerance agreed with the "
        "application team, and no class shows CONFLICTS FOUND [R19]. Pega documents the rebuild steps and screens [R17].")
    b.h2("Backups and restore")
    b.p("Every index can be rebuilt from the Pega database, so OpenSearch snapshots are optional. They shorten recovery but "
        "add storage cost.")
    b.table(["Choice", "Recovery after loss of the OpenSearch service", "Recovery time"], [
        ["No snapshots", "Recreate the service, apply the cluster settings, restart SRS, run a full index build", "Measured full build time plus provisioning time"],
        ["Provider snapshots", "Restore the latest snapshot, then reindex classes changed since the snapshot", "Restore time plus a partial build; measure in PERF"],
    ], caption="Recovery choices for search", widths=[3.2, 8.6, 4.8], size=9)
    b.p("Elasticsearch 8.x snapshots cannot be restored into OpenSearch [R38, R39], and the 8.8 embedded indexes are not in a "
        "snapshot-ready form, so snapshots play no part in moving from 8.8.")


def s8_secrets(b):
    b.h1("Secrets, certificates and identity")
    b.p("No password, key or JAAS string is written in a Helm values file. The Pega Helm charts support external secrets for "
        "the database, stream, SRS OAuth and certificates [R23]. Key Vault is the system of record, one vault per environment, "
        "and the External Secrets Operator copies secrets into Kubernetes [R48].")
    b.figure(GEN + "fig_secrets_flow.png", "Secret delivery from Key Vault to Pega, installer and SRS pods", OWN, width_cm=16)
    b.h2("Secret inventory")
    b.p("{ref:tab_secrets} lists every secret. Key names marked as fixed are required by the Pega charts; the secret names "
        "are this design's convention.")
    b.table(["Kubernetes secret", "Keys", "Used by", "Key Vault secrets", "Key names"], [
        ["pega-db-secret", "DB_USERNAME, DB_PASSWORD", "Pega tiers and installer job (`global.jdbc.external_secret_name`)", "`pega-db-username`, `pega-db-password`", "Fixed [R23]"],
        ["pega-stream-secret", "STREAM_TRUSTSTORE_PASSWORD, STREAM_KEYSTORE_PASSWORD, STREAM_JAAS_CONFIG", "Pega tiers (`stream.external_secret_name`)", "`stream-truststore-password`, `stream-keystore-password`, `confluent-jaas`", "Fixed [R23]"],
        ["pega-srs-oauth", "SRS_OAUTH_PRIVATE_KEY", "Pega tiers (`pegasearch.srsAuth.external_secret_name`)", "`okta-srs-private-key`", "Fixed [R23]"],
        ["srs-search-credentials", "username, password", "SRS (`srs.srsStorage.authSecret`)", "`opensearch-srs-username`, `opensearch-srs-password`", "Per SRS README [R24]"],
        ["srs-runtime-certs", "keystore and truststore files, keystorePassword, truststorePassword", "SRS (`srs.srsRuntime.ssl.certsSecret`)", "`srs-tls-keystore`, `srs-tls-truststore`, passwords", "Per SRS README [R24]"],
        ["pega-tier-tls", "TOMCAT_KEYSTORE_CONTENT, TOMCAT_KEYSTORE_PASSWORD, ca.crt", "Web tier TLS (`tier.service.tls.external_secret_names`)", "`pega-tls-keystore`, `pega-tls-password`, `pega-tls-ca`", "Fixed [R23]"],
    ], widths=[2.8, 3.8, 3.8, 4, 2.2], caption="Secret inventory (one set per environment, in kv-pega-<code>)", size=8, label="secrets")
    b.h2("External Secrets Operator manifests")
    b.code("""apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: keyvault
  namespace: pega-<code>
spec:
  provider:
    azurekv:
      authType: WorkloadIdentity
      vaultUrl: "https://kv-pega-<code>.vault.azure.net"
      serviceAccountRef:
        name: eso-keyvault-reader
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pega-stream-secret
  namespace: pega-<code>
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: keyvault
    kind: SecretStore
  target:
    name: pega-stream-secret
  data:
    - secretKey: STREAM_TRUSTSTORE_PASSWORD
      remoteRef: { key: stream-truststore-password }
    - secretKey: STREAM_KEYSTORE_PASSWORD
      remoteRef: { key: stream-keystore-password }
    - secretKey: STREAM_JAAS_CONFIG
      remoteRef: { key: confluent-jaas }
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pega-srs-oauth
  namespace: pega-<code>
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: keyvault
    kind: SecretStore
  target:
    name: pega-srs-oauth
  data:
    - secretKey: SRS_OAUTH_PRIVATE_KEY
      remoteRef: { key: okta-srs-private-key }""", title="SecretStore and ExternalSecrets for the Pega namespace (Azure Key Vault provider [R48])")
    b.p("Create the same pattern for `pega-db-secret` and `pega-tier-tls` in `pega-<code>`, and for `srs-search-credentials` "
        "and `srs-runtime-certs` in `srs-<code>`. Each namespace has its own SecretStore and workload identity, and that "
        "identity can read only its own environment's vault.")
    b.callout("note", "Check which External Secrets Operator API version is installed (`v1beta1` or `v1`) and use it. The "
              "stream truststore and keystore password keys can hold empty values with SASL/PLAIN and a public CA, but keep the "
              "keys in the order the chart expects [R23].")
    b.h2("Rotation")
    b.table(["Secret", "Steps", "Restart needed"], [
        ["Confluent API key", "Create a second key for the same service account; write the new JAAS value to Key Vault; wait for or force the External Secrets refresh; rolling restart of the Pega tiers; check the Stream landing page; delete the old key", "Yes, Pega tiers"],
        ["OpenSearch SRS user password", "Change the password on the provider; update Key Vault; refresh; restart SRS; check search (S-5)", "Yes, SRS"],
        ["Okta client key", "Add the new public key to the Okta app; update `okta-srs-private-key`; refresh; restart Pega tiers; check search; remove the old public key", "Yes, Pega tiers"],
        ["Database password", "Per the DBA process; update Key Vault; refresh; restart Pega tiers", "Yes"],
    ], caption="Secret rotation", widths=[3.4, 10.4, 2.8], size=8.5)
    b.callout("caution", "Pods read these values at start. A new Key Vault version reaches the Kubernetes secret on the next "
              "refresh, but running pods keep the old value until they restart. A rotation without a restart works until the "
              "old credential is deleted, then fails (FS-20).")
    b.h2("Certificates")
    b.table(["Certificate", "Issued by", "Used for", "Renewal owner"], [
        ["Public TLS certificate for the Pega host name", "Customer public CA", "Application Gateway listener", "Platform team"],
        ["Web tier backend certificate", "Customer private CA", "Application Gateway to web pods", "Platform team"],
        ["SRS server certificate", "Customer private CA", "Pega to SRS TLS", "Platform team"],
        ["Confluent broker certificates", "Confluent (public CA)", "SASL_SSL from Pega", "Confluent"],
        ["OpenSearch endpoint certificate", "Provider or customer CA", "SRS to OpenSearch TLS", "OpenSearch provider"],
        ["Okta endpoint certificate", "Okta (public CA)", "Token and key set calls", "Okta"],
    ], caption="Certificates", widths=[5, 3.6, 4.4, 3.6], size=9)
    b.callout("caution", "Do not route Pega-to-Confluent, SRS-to-OpenSearch or Okta traffic through a TLS-inspecting proxy. "
              "Re-signed certificates break the trust chain that the clients check.")
