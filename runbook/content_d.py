"""Sections 10 to 12: Helm configuration, the cloned database, the 8.8 content question."""
from content_a import GEN, PUB, OWN
import envs as E
import values_gen as V


def s9_helm(b):
    b.h1("Helm configuration per environment")
    b.h2("Chart version and the three runs")
    b.p("This design uses Pega Helm charts 4.13.0: the `pega` chart for Pega Platform and the installer job, and the "
        "`backingservices` chart for SRS [R23, R24]. Every key in this section and in Appendix B was checked against the README "
        "and default values file of that chart version. Each environment built from a clone goes through three Helm runs of "
        "the `pega` chart, shown in {ref:tab_runs}.")
    b.table(["Run", "global.actions.execute", "What runs", "Why"], [
        ["U: upgrade", "`upgrade`", "Installer job only; no Pega pods", "Upgrades the cloned database. Pega must not start until the clean-up in Section 11.3 is done."],
        ["F: first start", "`deploy`", "Web tier only; batch tier `replicas: 0` with HPA off", "No queue processor, job scheduler or real-time data flow runs while cloned items are checked (Section 11.4)."],
        ["D: steady state", "`deploy`", "Web and batch tiers at normal size", "Index build, then normal operation."],
    ], caption="Helm runs of the pega chart for an environment built from a clone", widths=[2.6, 3.2, 4.6, 6.2], size=9, label="runs")
    b.p("The chart's actions are `install`, `deploy`, `install-deploy`, `upgrade` and `upgrade-deploy` [R23]. "
        "`upgrade-deploy` is not used, because it would start Pega straight after the upgrade, before the cloned items are "
        "checked.")
    b.h3("Upgrade type")
    b.p("The chart supports the upgrade types `in-place` (rules and data in one run, with downtime), `out-of-place-rules` and "
        "`out-of-place-data` (a two-step out-of-place upgrade), `zero-downtime` and `custom` [R23]. The chart default is "
        "`in-place`. The zero-downtime type needs REST credentials for the running pre-upgrade system to perform pre- and "
        "post-actions [R23], and a cloned database has no running 8.8 system attached. The design therefore uses `in-place` on "
        "the clone, which is disposable until the cutover, and asks Pega Support to confirm it (GQ-04).")
    b.h2("Pega chart keys per environment")
    b.p("{ref:tab_pega_keys} lists every `pega` chart key this design sets, with its value per environment. Keys not listed "
        "keep the chart default. Values in angle brackets are recorded in Appendix A.")
    rows = [
        ["`global.provider`", "Kubernetes provider"] + ["`aks`"] * 6 + ["[R23]"],
        ["`global.actions.execute`", "Run type ({ref:tab_runs})"] + ["U / F / D"] * 6 + ["[R23]"],
        ["`global.customerDeploymentId`", "Index prefix and `guid` value"] + [f"`{E.deployment_id(c)}`" for c in E.CODES] + ["[R23]"],
        ["`global.jdbc.url`", "Upgraded clone for this environment"] + ["`<jdbc-url>`"] * 6 + ["[R23]"],
        ["`global.jdbc.external_secret_name`", "DB_USERNAME, DB_PASSWORD"] + ["`pega-db-secret`"] * 6 + ["[R23]"],
        ["`global.jdbc.rulesSchema`, `dataSchema`", "Schemas of the clone"] + ["`<rules-schema>`"] * 6 + ["[R23]"],
        ["`global.docker.pega.image`", "Pega image"] + ["`platform/pega:26.1.1`"] * 6 + ["[R23]"],
        ["`tier[web].replicas` and HPA min / max", "Web pods"] + [f"{V.SIZES[c][0]} / {V.SIZES[c][1]}" for c in E.CODES] + ["[R23]"],
        ["`tier[batch].replicas` and HPA min / max", "Batch pods (run F: 0, HPA off)"] + [f"{V.SIZES[c][2]} / {V.SIZES[c][3]}" for c in E.CODES] + ["[R23]"],
        ["`tier[*].pdb.enabled`", "Pod disruption budget"] + ["`true`"] * 6 + ["[R23]"],
        ["`tier[*].resources`", "Memory, CPU request / limit"] + ["12Gi, 3 / 4"] * 6 + ["[R23]"],
        ["`tier[*].topologySpreadConstraints`", "Spread over zones (Section 4.6)"] + ["zone, skew 1"] * 6 + ["[R61]"],
        ["`tier[web].service.tls.external_secret_names`", "Backend TLS keystore"] + ["`pega-tier-tls`"] * 6 + ["[R23]"],
        ["`tier[web].ingress.domain`", "Host name"] + ["`<pega-host>`"] * 6 + ["[R23]"],
        ["`cassandra.enabled`", "No Decision Data Store"] + ["`false`"] * 6 + ["[R23]"],
        ["`hazelcast.enabled`, `clusteringServiceEnabled`", "Hazelcast removed in '25"] + ["`false`"] * 6 + ["[R5, R23]"],
        ["`stream.enabled`", "Stream service on"] + ["`true`"] * 6 + ["[R23]"],
        ["`stream.bootstrapServer`", "Confluent bootstrap"] + [f"`{E.cluster(g)}`" for _, _, g in E.ENVS] + ["[R23]"],
        ["`stream.securityProtocol`", "TLS and SASL"] + ["`SASL_SSL`"] * 6 + ["[R23]"],
        ["`stream.saslMechanism`", "API key"] + ["`PLAIN`"] * 6 + ["[R23]"],
        ["`stream.streamNamePattern`", "Topic prefix"] + [f"`{E.pattern(c)}`" for c in E.CODES] + ["[R23]"],
        ["`stream.replicationFactor`", "Replicas per partition"] + ["`3`"] * 6 + ["[R23]"],
        ["`stream.external_secret_name`", "STREAM_* keys"] + ["`pega-stream-secret`"] * 6 + ["[R23]"],
        ["`pegasearch.externalSearchService`", "Use SRS"] + ["`true`"] * 6 + ["[R23]"],
        ["`pegasearch.externalURL`", "SRS service, HTTPS port 8443"] + [f"`srs-{c}:8443`" for c in E.CODES] + ["[R23, R62]"],
        ["`pegasearch.srsAuth.enabled`", "OAuth to SRS"] + ["`true`"] * 6 + ["[R23]"],
        ["`pegasearch.srsAuth.url`", "Okta token endpoint"] + ["non-prod server"] * 5 + ["PROD server", "[R23, R43]"],
        ["`pegasearch.srsAuth.clientId`", "Okta client"] + [f"`pega-srs-{c}`" for c in E.CODES] + ["[R23]"],
        ["`pegasearch.srsAuth.scopes`", "Scope"] + ["`pega.search:full`"] * 6 + ["[R23]"],
        ["`pegasearch.srsAuth.authType`", "Client authentication"] + ["`private_key_jwt`"] * 6 + ["[R23]"],
        ["`pegasearch.srsAuth.privateKeyAlgorithm`", "Key algorithm"] + ["`RS256`"] * 6 + ["[R23]"],
        ["`pegasearch.srsAuth.external_secret_name`", "SRS_OAUTH_PRIVATE_KEY"] + ["`pega-srs-oauth`"] * 6 + ["[R23]"],
        ["`pegasearch.srsMTLS.enabled`", "Mutual TLS to SRS"] + ["`false`"] * 6 + ["[R23]"],
        ["`installer.image`", "Installer image"] + ["`installer:26.1.1`"] * 6 + ["[R23]"],
        ["`installer.upgrade.upgradeType`", "Upgrade type (GQ-04)"] + ["`in-place`"] * 6 + ["[R23]"],
    ]
    b.table(["Key", "Meaning"] + E.NAMES + ["Source"], rows, caption="Pega chart keys per environment (chart 4.13.0)",
            widths=[3.5, 2.5, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.25], size=6.5, label="pega_keys")
    b.callout("note", "Starting replica counts are sized for function, not load. Set the PERF, PREPROD and PROD values from the "
              "PERF load test (Section 16), and keep PREPROD equal to PROD.")
    b.h3("Topology spread, heap and garbage collection logging")
    b.bullets([
        "`topologySpreadConstraints` is read by the tier template of chart 4.13.0 [R61] but is not listed in the README, so check it in the `helm template` output after every chart upgrade. The label selector must match the pod label the chart sets, `app: <deployment name>-<tier name>`, for example `app: pega-web`.",
        "The chart defaults the Pega container to 12Gi of memory with a commented heap of 8192m [R23]. Keep the heap at about two thirds of the container memory: the JVM also needs native memory for threads, metaspace, Kafka client buffers and the code cache, and a container that exceeds its limit is killed without a Java error.",
        "Set the JVM arguments Pega recommends in `tier[*].javaOpts` [R63]: garbage collection logging to `/usr/local/tomcat/logs/gc.log`, `-XX:MaxMetaspaceSize=768m` so metaspace cannot exhaust node memory, `-XX:+UseStringDeduplication` and `-XX:+HeapDumpOnOutOfMemoryError`. The values files in Appendix B carry them. GC logs and heap dumps are on ephemeral pod storage, so the log collector must tail the GC file (Section 19.2).",
        "Pega images run in Etc/UTC. If the cloned 8.8 database does not use UTC, set `-Duser.timezone` to the database time zone in `javaOpts` and in the installer's `customJVMArgs` as well [R63]. A mismatch between the two shifts delayed queue items and job scheduler times.",
        "Long GC pauses show up as Kafka consumer group rebalances and as SRS request timeouts, so the GC log is the first thing to read when those appear (Section 18).",
        "Set `pegaDiagnosticUser` and its password through the diagnostic secret, so support staff can download Tomcat logs without a redeploy [R23].",
    ])
    b.h2("Backingservices chart keys per environment")
    rows = [
        ["`global.k8sProvider`", "Provider"] + ["`aks`"] * 6 + ["[R24]"],
        ["`srs.deploymentName`", "SRS release"] + [f"`srs-{c}`" for c in E.CODES] + ["[R24]"],
        ["`srs.srsRuntime.replicaCount`", "SRS pods"] + [str(V.SIZES[c][4]) for c in E.CODES] + ["[R14, R24]"],
        ["`srs.srsRuntime.srsImage`", "SRS image"] + ["`-os:<tag>`"] * 6 + ["[R14, R24]"],
        ["`srs.srsRuntime.env.AuthEnabled`", "Token checks"] + ["`true`"] * 6 + ["[R24]"],
        ["`srs.srsRuntime.env.OAuthPublicKeyURL`", "Okta key set"] + ["non-prod server"] * 5 + ["PROD server", "[R24, R42]"],
        ["`srs.srsRuntime.ssl.*`", "TLS on SRS"] + ["`enabled`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.provisionInternalESCluster`", "External search"] + ["`false`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.domain`", "OpenSearch host"] + [f"`{E.search(g)}`" for _, _, g in E.ENVS] + ["[R24]"],
        ["`srs.srsStorage.port`, `protocol`", "Endpoint"] + ["`443`, `https`"] * 6 + ["[R24]"],
        ["`srs.srsRuntime.resources`", "CPU request / limit, memory"] + ["1 / 2, 4Gi"] * 6 + ["[R14, R24]"],
        ["`srs.srsRuntime.affinity`", "Zone anti-affinity"] + ["preferred"] * 6 + ["[R24]"],
        ["`srs.srsStorage.tls.enabled`", "Certificate authentication, not encryption ({ref:tab_srs_traps})"] + ["`false`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.basicAuthentication.enabled`", "SRS user"] + ["`true`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.authSecret`", "username, password"] + ["`srs-search-credentials`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.requireInternetAccess`", "No internet egress"] + ["`false`"] * 6 + ["[R24]"],
        ["`srs.srsStorage.networkPolicy.enabled`", "Chart policy off; own policy (Section 7.7)"] + ["`false`"] * 6 + ["[R62]"],
    ]
    b.table(["Key", "Meaning"] + E.NAMES + ["Source"], rows, caption="Backingservices chart keys per environment",
            widths=[3.5, 2.5, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.25], size=6.5, label="srs_keys")
    b.h2("Differences between the runs")
    b.p("Only two places change between runs: the action, and the batch tier size. {ref:tab_run_diff} shows them for SIT; PROD "
        "is the same with its own sizes. Appendix B has the complete files for SIT and PROD.")
    b.table(["Key", "Run U (upgrade)", "Run F (first start)", "Run D (steady state)"], [
        ["`global.actions.execute`", "`upgrade`", "`deploy`", "`deploy`"],
        ["`tier[batch].replicas`", "not used", "`0`", "`1` in SIT, `3` in PROD"],
        ["`tier[batch].hpa.enabled`", "not used", "`false`", "`true`"],
        ["`installer.*`", "used", "ignored", "ignored"],
    ], caption="Values that change between runs", widths=[4.4, 3.6, 4, 4.6], size=9, label="run_diff")
    b.h2("Pipeline rules")
    b.bullets([
        "Keep one values file per environment and run in Git. Each change goes through review by the platform team and the Pega LSA.",
        "Pin the chart version (`helm upgrade --install ... --version 4.13.0`) and record image digests in Appendix A.",
        "Run `helm template` and `helm lint` with the values file in the pipeline before every apply.",
        "Fail the pipeline if a values file contains a literal password, API secret, JAAS string or private key. Secrets come only through `external_secret_name` keys.",
        "Fail the pipeline if `customerDeploymentId` or `streamNamePattern` does not match the environment's row in {ref:tab_naming}.",
    ])


def s10_clone(b):
    b.h1("The cloned database")
    b.p("A database cloned from 8.8 production carries 8.8 settings, records and work. Some of it refers to the embedded Kafka "
        "and embedded Elasticsearch that no longer exist, and some of it points at production systems. This section lists "
        "what must be confirmed with Pega Support, what must be cleaned up, and the controlled first start that every "
        "cloned environment follows.")
    b.h2("Gating questions for Pega Support")
    b.p("Pega's pages say that Hazelcast must be removed before updating to '25 or later, and that this applies to embedded "
        "Hazelcast and the Clustering Service [R5]. They do not say how this applies to a database that is cloned, upgraded "
        "offline and only ever started on 26.1.1. {ref:tab_gq} lists the questions to raise in one Pega Support case before M2. "
        "Any condition Pega sets becomes a mandatory step in Section 13.7.")
    b.table(["ID", "Question", "Why it matters", "Evidence found", "Answer", "Date"], [
        ["GQ-01", "Is a direct upgrade of an 8.8 database to 26.1.1 with the 26.1.1 installer supported?", "The whole path depends on it", "Not settled by the pages read", "Open", ""],
        ["GQ-02", "Which 8.8 patch level is required before the clone?", "May need an 8.8 patch in production before the final clone", "Not settled", "Open", ""],
        ["GQ-03", "Does the Hazelcast removal requirement apply to a clone upgraded offline? If so, which settings must be in the database before the upgrade?", "Pega states removal is required before updating to '25 [R5]; the removal steps assume a running system [R6]", "Not settled for this case", "Open", ""],
        ["GQ-04", "Which installer upgrade type suits a cloned database: `in-place`, or `out-of-place-rules` then `out-of-place-data`?", "Sets run U and the outage length", "Chart types listed in [R23]", "Open", ""],
        ["GQ-05", "How does 26.1.1 treat 8.8 stream and search DSS and node records in an upgraded database, and which takes precedence: DSS in the database or Helm settings?", "A stale DSS could override the Helm configuration", "Not settled; tested as FS-24", "Open", ""],
        ["GQ-06", "How are 8.8 delayed and broken queue items processed after the upgrade, given the '26 queue processing changes?", "Items may fail or run unexpectedly", "'26 changes queue processing [R3]", "Open", ""],
        ["GQ-07", "Is any SRS or customerDeploymentId state stored in the database that a clone would carry?", "Could link a clone to another environment's indexes", "Not settled; tested as IT-05", "Open", ""],
        ["GQ-08", "Does the 26.1.1 installer need a Kafka connection while it upgrades an 8.8 database, and if so how is it supplied in the Helm installer job?", "Run U could fail or stall; chart 4.13.0 passes no stream settings to the installer job", "From '25, Pega command-line tooling needs Kafka [R8]; rendered run U has no `STREAM_*` values", "Open", ""],
        ["GQ-09", "Are page snapshots in queue processor messages, delayed items and broken items encrypted when the class uses BLOB encryption or a PropertyEncrypt policy?", "Decides whether Restricted data sits in plaintext on Kafka and in queue tables (Section 9.3)", "BLOB encryption does not cover exposed columns [R71]; queue payloads not covered", "Open", ""],
        ["GQ-10", "What do the cluster messages that replaced Hazelcast carry over Kafka in 26.1.1, and can they include case or clipboard data?", "Sets the data class of those topics (D-05)", "Kafka carries the messaging Hazelcast carried [R7]; content not published", "Open", ""],
        ["GQ-11", "In SRS mode, are index documents removed when a record is deleted, purged or archived, and how soon?", "Erasure requests and retention depend on it (Section 9.7)", "Not settled; tested as DT-06", "Open", ""],
    ], caption="Gating questions for Pega Support", widths=[1.3, 4.6, 3.6, 3.2, 1.6, 1.3], size=8, label="gq")
    b.callout("important", "Until the answers arrive, the plan assumes the conservative answer for each question: rehearse the "
              "full path twice, apply the clean-up in Section 11.3, and treat any difference from expected behaviour as a "
              "stop condition at the first-start Go/No-Go.")
    b.h2("How Helm settings and database settings interact")
    b.p("Pega 26.1.1 gets its stream and search configuration from the Helm chart. A cloned 8.8 database may also hold Dynamic "
        "System Settings (DSS) for the stream service or for search. Pega documents the stream setting names, for example "
        "`services/stream/provider`, `services/stream/broker/url` and `services/stream/name/pattern` [R8]. The pages read do "
        "not settle whether a DSS with such a name in the database would override the value the Helm chart supplies. The "
        "design therefore treats it as a risk: search the cloned DSS for any setting that contains `services/stream` or refers "
        "to search hosts, record them, and prove in the first DEV start that the landing pages show the Helm values (FS-24). "
        "GQ-05 asks Pega Support for the rule.")
    b.h2("Inventory and clean-up")
    b.p("{ref:tab_inventory} lists the items that affect Kafka and search. For each one it gives where it lives, what 26.1.1 "
        "does with it, the risk, the action, when the action happens and the source. Time points are: B (before the upgrade, "
        "on the clone), A (after the upgrade, before the first start), F (during the first start, with the batch tier at "
        "zero), and S (after the first start). No table names are given: Pega has not published them for these items, and "
        "each change uses the Pega screen named.")
    b.figure(GEN + "fig_decision_cloned_item.png", "Decision: treatment of an item found in the cloned database", OWN, width_cm=12)
    b.table(["ID", "Item", "Where it lives", "26.1.1 behaviour", "Risk", "Action", "When", "Source"], [
        ["CD-01", "Stream service DSS from 8.8 (provider, broker URL, name pattern, replication)", "DSS (Records > SysAdmin > Dynamic System Settings)", "Helm supplies the stream settings; precedence not documented", "Stale value overrides Helm", "Record; check landing page shows Helm values; remove only as Pega Support advises (GQ-05)", "F", "[R8, R12]"],
        ["CD-02", "Embedded stream node records from 8.8", "Stream service landing page (Configure > Decisioning > Infrastructure > Services > Stream)", "External Kafka has no stream nodes", "Landing page shows unavailable 8.8 nodes; confusion during checks", "Check; remove stale entries from the landing page if shown", "F", "[R13]"],
        ["CD-03", "Search settings and index host node records from 8.8 embedded Elasticsearch", "DSS and search landing page", "SRS configured by Helm replaces embedded search", "Stale setting points search at 8.8 nodes", "Check search landing page shows SRS; record and remove stale settings as Pega Support advises", "F", "[R14, R16]"],
        ["CD-04", "Search index status from 8.8", "Search landing page", "Indexes are rebuilt through SRS", "Status shows old indexes as present", "Full index build; check status [R19]", "S", "[R15, R19]"],
        ["CD-05", "Delayed queue items", "Database (queue processor delayed items)", "Become due and are queued to Kafka when their time arrives", "Items run on 26.1.1 against changed rules, or call production systems from a clone", "Count on 8.8 before the clone; in non-production, decide per queue processor to discard or keep; in PROD, keep and test in PREPROD (GQ-06)", "B, S", "[R3]"],
        ["CD-06", "Broken queue items", "Database (queue processor broken items, shown in Admin Studio)", "Stay broken until requeued or deleted", "Requeue on 26.1.1 runs old work with new rules", "Resolve on 8.8 before the final clone where possible; record counts; decide per queue processor", "B, S", "[R3]"],
        ["CD-07", "Job scheduler state", "Job scheduler rules and their run state", "Job schedulers run on batch nodes after start", "Clone runs production jobs (email, extracts) on first start", "Batch tier at zero in run F; disable jobs that call external systems in non-production before scaling the batch tier", "F", "[R11]"],
        ["CD-08", "Data flow runs, including real-time runs on Kafka data sets", "Data flow landing pages", "Runs restart against 26.1.1 topics or the customer's Kafka", "Runs resume against old offsets or production topics", "Stop or delete runs that refer to 8.8 stream partitions; restart from the agreed point", "F, S", "[R11]"],
        ["CD-09", "Kafka configuration instances and Kafka data sets for application integrations", "Records > SysAdmin > Kafka; Records > Data Model > Data Set", "Connect to the customer's own Kafka clusters", "A non-production clone reads production topics and moves production consumer offsets", "Repoint to test clusters or disable in every non-production environment; decide per data set in PROD (Section 12.3)", "F", "[R11]"],
        ["CD-10", "Other production endpoints: connectors, listeners, email accounts, file listeners", "Integration rules and data instances", "Run on start if enabled", "A clone calls or polls production systems", "Short checklist owned by the application team; firewall denies production endpoints from non-production", "F", "Customer"],
        ["CD-11", "DSS `delayeditems/dataflowbased/threadspernode`", "DSS", "No longer used in '26", "PEGA0179 alert", "Delete", "A", "[R3]"],
        ["CD-12", "Hazelcast-related settings from 8.8", "DSS and prconfig values", "Hazelcast removed in '25", "Unknown until GQ-03 is answered", "Apply Pega Support's instructions", "B or A", "[R5]"],
        ["CD-13", "Tables without primary keys", "Database", "Required for '25 and later", "Upgrade blocked", "Run primaryKeyUtility as the DBA team plans", "B", "[R10]"],
        ["CD-14", "Custom search properties and reports that rely on search", "Rules", "Indexed by SRS after the build", "Feature behaves differently on SRS", "List them; include in the functional checks (Section 15.4)", "S", "[R14]"],
        ["CD-15", "Partition count DSS `prconfig/dsm/services/stream/pyTopicPartitionsCount/default` and per-topic partition changes made on 8.8", "DSS (ruleset Pega-Engine)", "Applies to every topic created at first start [R49]", "Partition count, and so Confluent capacity and cost, differs from the plan", "Record the value; keep or reset to 6 with the performance lead; recount with K-5", "A", "[R49]"],
        ["CD-16", "Pega Diagnostic Center endpoint and settings from production", "Configure > System > Settings", "Clone sends diagnostics to the production PDC endpoint [R51]", "Non-production alerts mixed with production in PDC", "Point each environment at its own PDC endpoint, or clear it", "F", "[R51]"],
    ], caption="Kafka and search items in the cloned database", widths=[1.1, 2.7, 2.5, 2.2, 2.3, 3.2, 0.9, 1.1], size=7, label="inventory")
    b.callout("caution", "Do not change these items with direct SQL against Pega tables unless Pega Support provides the "
              "statement for this release. Use the Pega screens named in the table during run F, when no background "
              "processing is running.")
    b.h2("First-start control")
    b.p("Every environment built from a clone follows the same scripted first start. {ref:tab_first_start} gives each step "
        "an owner, a check and the evidence to keep, and {ref:fig_gonogo} shows the Go/No-Go logic.")
    b.table(["Step", "Action", "Owner", "Check", "Evidence"], [
        ["ST-1", "Run U: upgrade the clone with the installer job", "Platform team, DBA", "Job completed; no errors in the log (P-5)", "Installer log"],
        ["ST-2", "Apply time-point A actions from {ref:tab_inventory}", "Pega LSA, DBA", "Each item signed off", "Clean-up record (Appendix D)"],
        ["ST-3", "Run F: deploy the web tier with this environment's prefix, service account and customerDeploymentId; batch tier at zero", "Platform team", "Web pods Ready (P-1)", "kubectl output"],
        ["ST-4", "Hold intake: no public DNS record, inbound listeners off, batch tier at zero", "Platform team, application team", "No user or inbound traffic in logs", "Ingress and listener status"],
        ["ST-5", "Check the Stream landing page and the Search landing page; apply time-point F actions", "Pega LSA", "Provider ExternalKafka, status NORMAL, prefix `pega-<code>-`; search uses SRS with `pega26-<code>`", "Screenshots"],
        ["ST-6", "Check the firewall log for denied connections to production or other environments", "Platform team", "No attempts, or each attempt traced to an item and fixed", "Firewall log extract"],
        ["ST-7", "Run D: scale the batch tier; start the full index build", "Platform team, Pega LSA", "Index build running; batch pods Ready", "Start time"],
        ["ST-8", "Check index completeness and counts (Section 7.8)", "Pega LSA", "All classes indexed; counts match", "Count sheet"],
        ["ST-9", "Release intake: public DNS, listeners and job schedulers as agreed", "Application team", "Smoke tests pass", "Test report"],
    ], caption="First-start steps for an environment built from a clone", widths=[1.3, 5.4, 2.6, 4.3, 3], size=8, label="first_start")
    b.figure(GEN + "fig_decision_first_start.png", "Decision: Go/No-Go at the first start", OWN, width_cm=9.5, label="gonogo")
    b.h2("Data protection and masking")
    b.p("Non-production clones of production data must follow the customer's masking policy. Mask the clone before the "
        "upgrade (time point B). The index build then reads only masked data, and no unmasked value reaches OpenSearch, "
        "Kafka topics or logs. If masking runs after the upgrade, it must still finish before run D, because the index build "
        "copies searchable data into OpenSearch. Masking after the index build leaves unmasked data in the indexes until a "
        "full rebuild. The masking approach is OD-07. Section 9.2 sets the data class that follows from it for each group.")
    b.callout("note", "Masking rules must keep values that integrations and searches depend on in a usable form, for example "
              "case IDs and keys used in search. Agree the rules with the application team, and include search checks on "
              "masked data in the functional tests.")


def s11_migration(b):
    b.h1("The 8.8 content question")
    b.h2("Answer")
    b.p("Nothing in the 8.8 Kafka or search storage is migrated. {ref:fig_migr} shows the decision for each kind of content, "
        "and {ref:tab_migr} gives the treatment and the evidence. Each statement was checked against the current Pega pages "
        "on the evidence cut-off date.")
    b.figure(GEN + "fig_decision_migration.png", "Decision: does 8.8 content need migrating?", OWN, width_cm=12, label="migr")
    b.h2("Treatment per content type")
    b.table(["Content", "Answer", "How it is handled", "Evidence"], [
        ["Pega stream data in Kafka (queue processor messages, data flow partitions)", "Not migrated", "Pega states existing stream data cannot be moved to a new Kafka. 8.8 uses embedded Kafka, so there is no external cluster to drain to. Before the production clone, hold intake on 8.8, wait until queue processors show nothing ready to process, record the counts and any broken items, then stop 8.8. 26.1.1 starts with empty topics that it creates under `pega-prd-`.", "[R13, R25]"],
        ["Queue items held in the database (delayed, broken)", "Travel with the clone", "Database content, not Kafka content. Handled as items CD-05 and CD-06 (Section 11.3) and tested in rehearsal.", "[R3]"],
        ["Topic names and configuration", "Not migrated", "26.1.1 creates its own topics under its own prefix. Only the topic settings policy, such as `max.message.bytes`, carries over as configuration.", "[R11, R23]"],
        ["Search indexes (embedded Elasticsearch on 8.8)", "Not migrated", "The indexes live on the 8.8 nodes, not in the database. They are built from the upgraded database after Pega connects to SRS, which needs downtime; the time is measured in rehearsal (Section 7.8). Elasticsearch 8.x snapshots cannot be restored into OpenSearch.", "[R15, R17, R38, R39]"],
        ["Application Kafka data sets on the customer's own topics", "Decided per data set", "Keep the existing cluster and topic, point at a new cluster, or mirror with Confluent Cluster Linking, which keeps offsets. Agree the start offset so messages are neither skipped nor processed twice.", "[R11, R35]"],
        ["Custom search data (custom search properties, reports that depend on search)", "Rebuilt and verified", "Rebuilt by the full index build; verified with count comparisons and functional checks.", "[R18, R19]"],
    ], caption="Treatment of 8.8 content", widths=[3.6, 2.2, 8.6, 2.2], size=8.5, label="migr")
    b.h2("Application Kafka data sets")
    b.p("Application Kafka data sets read from or write to the customer's own Kafka clusters, which are separate from the Pega "
        "stream service [R11]. Each one is decided on its own, with the application owner ({ref:fig_ds}). In every "
        "non-production environment, every data set is repointed to a test topic or disabled before the batch tier starts, so a "
        "clone never consumes from a production topic or moves a production consumer group's offsets.")
    b.figure(GEN + "fig_decision_app_datasets.png", "Decision: treatment of each application Kafka data set", OWN, width_cm=12, label="ds")
    b.table(["Data set", "Direction", "Cluster and topic", "PROD treatment", "Start offset at cutover", "Non-production treatment", "Owner"], [
        ["<data set name>", "<consume or produce>", "<cluster / topic>", "<keep, new cluster, Cluster Linking>", "<offset rule and evidence>", "<test topic or disabled>", "<application owner>"],
    ], caption="Application Kafka data set register (one row per data set, completed with the application team)", widths=[2.3, 2, 2.6, 2.6, 2.6, 2.6, 1.9], size=8, label="ds_register")
    b.h2("Why the Stream Migration activity is not used")
    b.p("Pega provides a Stream Migration activity and a Helm chart guide for switching a running deployment from embedded "
        "Stream to an external Kafka, or between Kafka providers [R13, R25]. It drains the queues of a running system before "
        "the switch. This programme never switches the running 8.8 system to an external Kafka: 8.8 keeps its embedded Kafka "
        "until it stops, and 26.1.1 starts on a different system with its own Confluent cluster. Holding intake and letting "
        "the 8.8 queues empty gives the same result, an empty queue at the moment of the final clone, without changing 8.8.")
    b.h2("Statement for approval")
    b.callout("decision", "No Pega stream topic and no search index is copied from 8.8. Database-held queue items travel with "
              "the clone and are handled as listed in {ref:tab_inventory}. Application Kafka topics are handled one by one as "
              "listed in {ref:tab_ds_register}.")
