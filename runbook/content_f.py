"""Sections 17, 18, 20 and 21: known issues, troubleshooting, operations, risks and decisions."""
from content_a import GEN, PUB, OWN
import envs as E


def _issues(b, caption, rows):
    b.table(["Symptom", "Cause", "Prevention", "Fix"], rows, caption=caption, widths=[4, 3.8, 4.4, 4.4], size=8)


def s16_issues(b):
    b.h1("Known issues and challenges")
    b.p("These are the problems that come up in this kind of implementation. Each one names the symptom, the cause, how to "
        "prevent it and how to fix it.")
    b.h2("Cloned database")
    _issues(b, "Known issues: cloned database", [
        ["Landing pages show 8.8 values instead of the Helm values", "Stream or search DSS from 8.8 in the cloned database (CD-01, CD-03)", "Record cloned DSS before the first start; FS-24 in DEV; GQ-05", "Apply Pega Support's answer; restart the tiers"],
        ["A production Kafka consumer group's offsets move while 8.8 is still live", "A non-production clone started with its application Kafka data sets still pointing at production (CD-09)", "Batch tier at zero in run F; data sets repointed before run D; firewall denies production clusters", "Reset the production consumer group with the Kafka owner; repoint the data set"],
        ["Stream landing page lists unavailable nodes", "8.8 embedded stream node records in the clone (CD-02)", "Check at ST-5", "Remove stale entries on the landing page"],
        ["Queue items from 8.8 fail on 26.1.1", "Rules referenced by the item changed in the upgrade (CD-05, CD-06)", "Drain fully on 8.8; resolve broken items before the clone; decide per queue processor", "Fix and requeue, or discard with business approval"],
        ["Index build longer than planned", "Production-sized data; too few batch pods or data nodes", "Measure in PERF and PREPROD; scale for the build (Section 7.8)", "Add batch pods and data nodes; extend the window through the Go/No-Go"],
        ["Emails or extracts sent from a test environment", "Job schedulers and connectors in the clone (CD-07, CD-10)", "Batch tier at zero in run F; checklist; firewall", "Disable the job; inform recipients"],
    ])
    b.h2("Kafka and Confluent")
    _issues(b, "Known issues: Kafka and Confluent", [
        ["Client reaches bootstrap, then broker timeouts", "Broker names resolve to public IPs or not at all; zonal Private Link records missing [R32]", "N-4 to N-6 for every new cluster; synthetic DNS check", "Add the zonal records"],
        ["Too many partitions on a shared cluster", "Many queue processors per environment, multiplied by environments", "Measured budget (Section 6.7); alert at 70 %", "Add capacity or move an environment"],
        ["RecordTooLargeException", "Confluent topic default max.message.bytes below Pega's 5,000,000 [R33]", "K-6 after every deployment", "Raise the topic setting"],
        ["SASL authentication fails after a secret change", "JAAS value stored with wrong quoting or line breaks", "Store as one line; test with K-3 before restarting Pega", "Correct the Key Vault value; restart"],
        ["Old credential still in use after rotation", "Pods not restarted after the secret changed (FS-20)", "Restart is a rotation step", "Rolling restart"],
        ["Topic creation denied", "Security policy removed CREATE from the ACL", "Decide OD-11 early; pre-create topics if needed", "Restore CREATE or pre-create the topic"],
        ["Kafka outage stops more than queue processing", "From '25, Pega uses Kafka for cluster messaging that Hazelcast carried [R7]", "Treat Kafka as tier-1; FS-01", "Restore Kafka; check nodes reconnect"],
        ["Producer and consumer latency rises during restarts; brief stream errors", "Connection or request limits enforced on Enterprise clusters [R31]", "Measure connections per pod; stagger restarts in shared groups; FS-31", "Wait for throttling to end; restart in smaller steps"],
        ["First start or refresh takes far longer than planned", "Partition creation paced at 500 per five minutes per cluster [R31]", "Include topic creation time in rehearsals; one refresh per group at a time; FS-32", "Let creation finish; do not restart pods mid-way"],
        ["Partition count far above the budget after first start", "Cloned 8.8 partition DSS (CD-15) [R49]", "Record the DSS at time point A", "Reset the DSS; resize with `pxAlterStreamPartitions` if Pega Support agrees"],
        ["Adding batch pods does not increase throughput", "Consumers already equal partitions [R50]", "Effective consumer formula (Section 6.7)", "Raise partitions for the bottleneck queue processor"],
        ["Installer job stalls or logs Kafka connection errors", "Upgrade tooling may need Kafka (GQ-08) [R8]", "Allow installer egress to Confluent until GQ-08 is answered", "Supply the stream settings as Pega Support advises; rerun"],
    ])
    b.h2("OpenSearch and SRS")
    _issues(b, "Known issues: OpenSearch and SRS", [
        ["Indexes created with wrong names or settings, or index creation blocked", "Auto-creation not disabled, or SRS user lacks rights [R14]", "Apply cluster settings before SRS starts; IT-06", "Apply settings; widen the role by the missing permission only; rebuild"],
        ["SRS returns 401 or 403; Pega search fails", "Okta token missing `pega.search:full`, missing or wrong `guid`, or issued by the org authorization server [R42, R44]", "Custom authorization server; O-2 decode in every environment", "Fix the scope, claim or server; restart Pega if the client changed"],
        ["SRS will not start against OpenSearch", "SRS image not on the matrix for the OpenSearch version [R14]", "Pin versions per Section 7.2", "Use a matrix pair"],
        ["Old indexes remain after a refresh", "Refresh skipped the index clean-up", "Refresh checklist step (Section 20.3)", "Delete `pega26-<code>*` as the environment's SRS user, then rebuild"],
        ["Index deletion fails", "`destructive_requires_name` true [R14]", "OS-2", "Set to false"],
        ["`helm install` of SRS fails: \"Only one authentication can be enabled\"", "`srsStorage.tls.enabled` and basic authentication both true; `tls` means certificate authentication [R24]", "`tls.enabled: false`; `helm template` in the pipeline", "Set `tls.enabled: false`"],
        ["Pega search fails at first start; SRS pods healthy", "`externalURL` without `:8443`; SRS serves HTTPS on 8443 only [R62]", "URL with port; S-5 from the Pega namespace", "Correct the URL; restart the Pega tiers"],
        ["SRS pods never Ready; timeouts to OpenSearch and Okta", "Chart network policy allows egress only to an in-cluster Elasticsearch [R62]", "Chart policy off; own policy (Section 7.7)", "Disable the chart policy; apply the replacement"],
        ["Search fails for all environments at once", "Okta org rate limit reached on the token endpoint [R52]", "Token rate measured; System Log warnings alerted; FS-35", "Find the caller; lengthen token lifetime"],
        ["Search fails after an Okta key change", "SRS keeps an old signing key, or Pega's client key mismatches [R53]", "FS-33 and FS-34 in DEV", "Restart SRS; restore the client key"],
    ])
    b.h2("Platform")
    _issues(b, "Known issues: platform", [
        ["Most pods of a tier in one zone after a zone incident", "Spread is a scheduling preference; running pods are not moved back [R61]", "Check the spread after FS-21", "Rolling restart of the tier"],
        ["Pods killed with OOMKilled and no Java error", "Heap too close to the container memory limit", "Heap at about two thirds of the limit (Section 10.2)", "Lower the heap or raise the limit"],
        ["Delayed items and job schedulers run at the wrong hour", "JVM time zone differs from the cloned database [R63]", "`-Duser.timezone` in `javaOpts` and installer `customJVMArgs`", "Set both; restart"],
        ["GC logs and heap dumps lost after a crash", "Written to ephemeral pod storage [R23]", "Log collector tails the GC file (Section 19.2)", "Collect from the replacement pod; enable collection"],
    ])
    b.h2("Data protection")
    _issues(b, "Known issues: data protection", [
        ["Personal data found in a non-production index", "Masking ran after the index build, or a property was missed by the masking rules", "Mask before the upgrade (Section 11.5); DT-03 on every refresh", "Delete the environment's indexes (S-6) and rebuild after masking"],
        ["Self-managed key cannot be added to an existing Confluent cluster", "Encryption mode is fixed at creation [R74]", "OD-14 before the cluster is created", "Create a new cluster and move the environments; topics are recreated by Pega"],
        ["Confluent cannot reach the key on an Enterprise cluster", "Key Vault firewall blocks public access; Enterprise needs access from all networks [R74]", "Key-only vault for the Confluent key (Section 9.5)", "Correct the key vault networking; the cluster is unavailable while the key is unreachable"],
        ["Node pool without encryption at host", "Pool created before OD-18; the setting cannot be changed [R78]", "Pipeline check of `enableEncryptionAtHost` (DP-6)", "Add a new pool with the setting; drain and delete the old pool"],
        ["Search terms with personal data in OpenSearch slow logs", "Slow logs record the query [R58]", "Slow logs classified Restricted (Section 9.6)", "Restrict access; apply production log retention"],
        ["Broken items accumulate with case data", "Items left in the broken queue after incidents", "Broken item alert; OD-17 retention", "Requeue or delete after the cause is fixed"],
    ])
    b.h2("Process")
    b.p("Every refresh of a non-production environment from a new production clone repeats the risky parts of the first build: "
        "masking, topic and index clean-up, repointed integrations and a full reindex. Treat each refresh as a change with "
        "the checklist in Section 20.3, not as a database task alone.")


def s17_troubleshooting(b):
    b.h1("Troubleshooting")
    b.h2("Method")
    b.p("Most failures between Pega and Kafka or search are connectivity failures. Work through the chain in {ref:fig_chain} in "
        "order: a failure at one step makes every later step fail, so the first failing step is the one to fix. For cloned "
        "environments, first rule out a stale 8.8 setting (CD-01, CD-03).")
    b.figure(GEN + "fig_connectivity_chain.png", "Connectivity chain for Kafka and search", OWN, width_cm=16, label="chain")
    b.h2("Kafka")
    b.figure(GEN + "fig_troubleshoot_kafka.png", "Troubleshooting tree: stream service", OWN, width_cm=13.5)
    b.table(["Symptom", "Likely cause", "Check", "Fix"], [
        ["Stream status not NORMAL after start", "Stale cloned setting, DNS, network or authentication", "Landing page values; K-1 to K-3; Pega log", "Follow the tree"],
        ["Bootstrap works, brokers time out", "Zonal DNS records", "K-3", "Add records [R32]"],
        ["Topic or group authorization errors", "ACL prefix does not match `streamNamePattern`", "K-4, K-7", "Correct the prefix or ACL"],
        ["Transactional or idempotent producer errors", "Missing TRANSACTIONAL_ID or IDEMPOTENT_WRITE ACL", "K-7", "Add the ACL [R11]"],
        ["RecordTooLargeException", "Topic limit", "K-6", "Raise to 5,000,000"],
        ["Ready to process keeps growing", "Batch tier down or a failing processor", "Admin Studio; batch pod logs (P-2)", "Restore batch pods; fix the processor"],
        ["Throughput drops in one shared environment", "Quota reached, or another environment's load", "Metrics API by principal", "Adjust quota or schedule"],
    ], caption="Kafka symptoms", widths=[4, 4, 4, 4.6], size=8.5)
    b.h2("Search")
    b.figure(GEN + "fig_troubleshoot_search.png", "Troubleshooting tree: search", OWN, width_cm=13.5)
    b.table(["Symptom", "Likely cause", "Check", "Fix"], [
        ["SRS pods not Ready", "OpenSearch unreachable or wrong credentials", "SRS logs; S-1 from an SRS pod", "Fix network or `authSecret`; restart SRS"],
        ["401 or 403 in SRS log", "Token scope, `guid` or issuer", "O-2", "Fix Okta configuration"],
        ["Token request fails", "Firewall to Okta, client key mismatch", "O-1; Okta system log", "Fix rule or key"],
        ["Results missing for recent changes", "Indexing backlog", "Queue processors; Kafka tree", "Clear backlog"],
        ["Class shows CONFLICTS FOUND", "Mapping conflict in indexed properties [R19]", "Search landing page", "Fix the properties; reindex the class"],
        ["Cluster red or read-only", "Node loss or disk watermark", "S-2; provider console", "Restore capacity"],
    ], caption="Search symptoms", widths=[4, 4, 4, 4.6], size=8.5)
    b.h2("Cloned database and upgrade")
    b.table(["Symptom", "Likely cause", "Fix"], [
        ["Installer job fails", "Database connectivity, permissions, schema names, or a missing prerequisite", "Read the log (P-5); fix; rerun or restore the clone (FS-26)"],
        ["primaryKeyUtility reports insufficient space", "The utility copies each table missing a primary key", "Add database storage; rerun [R10]"],
        ["ClassNotFoundException for javax classes", "Custom JAR not rebuilt for Jakarta EE", "Import the rebuilt JAR into a higher CodeSet version [R9]"],
        ["PEGA0179 alerts", "Old queue processor DSS still present (CD-11)", "Delete the DSS [R3]"],
    ], caption="Cloned database and upgrade symptoms", widths=[4.6, 5.6, 6.4], size=8.5)
    b.h2("Support cases")
    b.p("Pega Global Client Support handles externalized services as it handles databases: it determines the cause, then "
        "hands over to the third-party provider if the issue is not in Pega software [R22]. Open cases with Pega logs from "
        "all tiers, Stream and search landing page screenshots, queue processor status, SRS logs, the Appendix C outputs, the "
        "decoded token claims, and the values file with secrets removed.")


def s19_ops(b):
    b.h1("Operations, onboarding, refresh and retirement")
    b.p("Monitoring, logging and alerting are in Section 19. This section covers the routine work that keeps the "
        "services healthy and the procedures for adding, refreshing and removing an environment.")
    b.h2("Routine tasks")
    b.table(["Task", "Frequency", "Owner", "Procedure"], [
        ["Confluent API key rotation", "Per security policy", "Kafka engineer", "Section 8.3"],
        ["OpenSearch SRS user password rotation", "Quarterly", "Search engineer", "Section 8.3"],
        ["Okta client key rotation", "Yearly or per policy", "Identity team", "Section 8.3"],
        ["Certificate renewal", "Before expiry", "Platform team", "Section 8.4"],
        ["Partition and shard capacity review", "Monthly and after each release", "Kafka and search engineers", "K-5, S-4"],
        ["Check new topics for max.message.bytes", "After each deployment", "Kafka engineer", "K-4, K-6"],
        ["SRS image update", "With Pega updates or security fixes", "Search engineer", "Update `srsImage` per environment, NP1 first"],
        ["OpenSearch version update", "Per provider notice, within the SRS matrix", "Search engineer", "NP1, then NP2, then PROD; rebuild if advised"],
        ["Cost review", "Quarterly", "Platform lead", "Cost model in Section 5.5 with actual usage"],
    ], caption="Routine operations", widths=[5, 3.6, 3.4, 4.6], size=8.5)
    b.h2("Onboarding a new non-production environment")
    b.steps([
        "Approve the environment and its group with the decision in Section 5.1. Assign a code that is not the start of another code.",
        "Add a row to {ref:tab_naming} and to Appendix A.",
        "Create the namespace, Key Vault, External Secrets identity and network policies (SI-1, SI-2, NW-5).",
        "Create the Okta client and, for option 2, add the client to the `guid` expression (Section 7.6).",
        "Create the service account, ACLs, quota and API key on the group's cluster (CC-2 to CC-4).",
        "Create the OpenSearch user and index-scoped role (OS-3, OS-4).",
        "Deploy SRS (SR-1 to SR-3).",
        "Clone, mask and upgrade the database (DB-1 to DB-5), then follow the first-start control (Section 11.4).",
        "Run the isolation tests against every other environment in the group.",
        "Add the environment to monitoring and the cost review.",
    ])
    b.h2("Refreshing an environment from a new clone")
    b.steps([
        "Agree the refresh window with the environment's users and the other environments in the group.",
        "Scale the environment's Pega tiers to zero.",
        "Delete its topics and consumer groups under `pega-<code>-` (K-9), and its indexes `pega26-<code>*` (S-6). Keep the prefix, customerDeploymentId, ACLs, quota, Okta client and SRS user.",
        "Take, mask and upgrade the new clone (DB-1 to DB-5).",
        "Follow the first-start control (Section 11.4), including repointing application Kafka data sets and other endpoints.",
        "Run the full index build and the functional checks.",
        "Record the refresh in the environment log with the evidence.",
    ])
    b.h2("Retiring an environment")
    b.steps([
        "Scale the Pega tiers and SRS to zero; uninstall the Helm releases.",
        "Delete the topics and consumer groups under the prefix (K-9).",
        "Delete the ACLs, API keys and service account (Section 6.5).",
        "Delete the indexes `pega26-<code>*` (S-6), then the OpenSearch user and role.",
        "Delete the Okta client and remove it from the `guid` expression.",
        "Delete the Key Vault secrets, External Secrets objects and the namespace; purge the vault per retention policy.",
        "Remove firewall rules and DNS records specific to the environment.",
        "Record evidence of each deletion in the retirement record (Appendix D).",
    ])
    b.h2("Roles and responsibilities")
    b.p("R = responsible, A = accountable, C = consulted, I = informed.")
    b.table(["Activity", "Platform team", "DBA team", "Kafka team", "Search team", "Pega team", "Pega Support", "Confluent", "OpenSearch provider"], [
        ["Network, DNS, firewall", "A/R", "I", "C", "C", "I", "I", "C", "C"],
        ["Confluent clusters, ACLs, quotas", "C", "I", "A/R", "I", "C", "I", "C", "I"],
        ["OpenSearch services, roles", "C", "I", "I", "A/R", "C", "I", "I", "R"],
        ["SRS deployment", "R", "I", "I", "A/R", "C", "C", "I", "I"],
        ["Okta authorization servers and clients", "C", "I", "I", "C", "C", "I", "I", "I"],
        ["Clone, masking, upgrade", "R", "A/R", "I", "I", "C", "C", "I", "I"],
        ["Cloned item clean-up", "C", "R", "C", "C", "A/R", "C", "I", "I"],
        ["Testing and rehearsals", "R", "R", "R", "R", "A/R", "I", "C", "C"],
        ["Cutover and rollback", "R", "R", "R", "R", "A/R", "C", "I", "I"],
        ["Operations after handover", "A/R", "R", "R", "R", "R", "C", "C", "C"],
    ], caption="RACI (Okta objects are owned by the customer identity team: A/R)", widths=[3.6, 1.6, 1.5, 1.5, 1.5, 1.5, 1.6, 1.6, 2.2], size=7.5)


def s20_risks(b):
    b.h1("Risks, open decisions, assumptions and source reconciliation")
    b.h2("Risk register")
    b.table(["ID", "Risk", "L", "I", "Mitigation", "Owner"], [
        ["RK-01", "Pega Support does not confirm the direct 8.8 to 26.1.1 clone-and-upgrade path, or sets conditions late", "M", "H", "Raise the case before M2 (OD-01); conservative plan; two rehearsals", "Pega LSA"],
        ["RK-02", "A stale 8.8 DSS overrides the Helm stream or search configuration", "M", "H", "FS-24 in DEV; GQ-05", "Pega LSA"],
        ["RK-03", "A non-production clone touches production Kafka topics or systems", "M", "H", "Batch tier at zero in run F; repointing; firewall deny; IT-09, IT-10", "Platform team"],
        ["RK-04", "Index build longer than the outage window", "M", "H", "Measure in PERF and PREPROD; scale for the build", "Search team"],
        ["RK-05", "Okta licence lacks custom authorization servers, or the client-based claim does not work for client credentials", "M", "H", "Check licence before M2; DEV test; fall back to option 1", "Identity team"],
        ["RK-06", "SRS needs cluster permissions beyond the index-scoped role", "M", "M", "IT-06 in DEV; widen only by named permissions", "Search team"],
        ["RK-07", "TRANSACTIONAL_ID `*` ACL is shared by all environments on a cluster", "L", "M", "Accepted residual risk; separate clusters for PROD", "Kafka team"],
        ["RK-08", "Noisy neighbour in a shared group", "M", "M", "Quotas; schedule; per-principal metrics", "Kafka team"],
        ["RK-09", "No OpenSearch provider passes the selection", "L", "H", "Self-managed fallback on AKS", "Enterprise architect"],
        ["RK-10", "Delayed or broken items fail after the upgrade", "M", "M", "Drain fully; resolve broken items; FS-28; GQ-06", "Pega LSA"],
        ["RK-11", "Masking breaks search or integration keys", "M", "M", "Masking rules agreed with the application team; search tests on masked data", "DBA team"],
        ["RK-12", "Vendor documentation changes between rehearsal and cutover", "M", "M", "Recheck Section 3 before each rehearsal", "Enterprise architect"],
        ["RK-13", "Confluent connection and request limits throttle Pega during restarts or peaks", "M", "M", "Measure connections and requests per pod; stagger restarts; throttle alert; FS-31", "Kafka team"],
        ["RK-14", "One Okta org rate limit shared by all environments and other applications", "M", "H", "Token rate measured; System Log alerts; token lifetime; FS-35", "Identity team"],
        ["RK-15", "The installer needs Kafka during the upgrade and the chart does not supply it", "L", "H", "GQ-08; installer egress to Confluent allowed in DEV", "Pega LSA"],
        ["RK-16", "Load test unrepresentative, so PROD is undersized", "M", "H", "Workload model from production logs; exit criteria in Section 16.5", "Performance lead"],
        ["RK-17", "Personal data copied to Kafka through page snapshots in queue messages", "M", "M", "Snapshot only with approval; DT-01; GQ-09", "Pega LSA"],
        ["RK-18", "Personal data in the shared services reachable by Confluent or OpenSearch administrators", "M", "H", "Index minimisation; break-glass access; audit logging; mask PREPROD (OD-15)", "Security architect"],
        ["RK-19", "Personal data leaked through logs, heap dumps or support cases", "M", "H", "Rules in Section 9.6; DT-09, DT-10", "Operations lead"],
        ["RK-20", "A key decision taken after the cluster or node pool exists forces a rebuild", "M", "M", "OD-14 and OD-18 decided by M2", "Security architect"],
        ["RK-21", "Unprocessed messages lost because consumer lag exceeded topic retention", "L", "H", "OD-16; lag drain alert; DT-08", "Kafka team"],
    ], caption="Risk register (L likelihood, I impact: H high, M medium, L low)", widths=[1.3, 5.6, 0.7, 0.7, 6, 2.3], size=8.5)
    b.h2("Open decisions")
    b.p("Each open decision has a recommended answer, an owner and the milestone by which it is needed (Section 14.2). If a "
        "decision is not taken by its milestone, the recommended answer applies and the risk is recorded.")
    b.table(["ID", "Decision", "Options", "Recommended answer", "Owner", "Needed by"], [
        ["OD-01", "Pega Support answers (GQ-01 to GQ-11)", "Answers received; conservative plan", "Raise now; plan conservatively until answered", "Pega LSA", "M2"],
        ["OD-02", "Confluent cluster types", "Enterprise; Dedicated", "Enterprise for NP1; PROD type for NP2 and PROD after PERF measurement", "Kafka team", "M2 (NP1), M3 (NP2, PROD)"],
        ["OD-03", "OpenSearch provider", "Third-party managed on Azure; self-managed on AKS", "Provider that passes Section 7.3", "Enterprise architect", "M2"],
        ["OD-04", "SRS per environment or shared", "Per environment; per group", "Per environment", "Search team", "M2"],
        ["OD-05", "Okta design", "Server per environment; shared non-production server", "PROD dedicated; shared non-production with client-based claim if proven", "Identity team", "M2"],
        ["OD-06", "Environment grouping", "Options A to D (Section 5.1)", "Option B", "Enterprise architect", "M1"],
        ["OD-07", "Masking approach", "Before upgrade; after upgrade before run D", "Before upgrade", "DBA team", "M2"],
        ["OD-08", "Treatment of each application Kafka data set", "Keep; new cluster; Cluster Linking", "Per data set ({ref:tab_ds_register})", "Application owner", "M4"],
        ["OD-09", "Quota approach", "Quotas per service account; no quotas", "Quotas in NP1 and NP2 from measured peaks", "Kafka team", "M3"],
        ["OD-10", "Kafka authentication", "SASL/PLAIN; SASL/OAUTHBEARER", "SASL/PLAIN", "Security architect", "M2"],
        ["OD-11", "Topic creation", "Pega creates (CREATE ACL); pre-created topics", "Pega creates", "Security architect", "M2"],
        ["OD-12", "Outage and rollback windows", "From rehearsal", "Rehearsal time plus 25 %", "Business owner", "M5"],
        ["OD-13", "OpenSearch snapshots", "None; provider snapshots", "Provider snapshots for PROD and NP2; none for NP1", "Search team", "M3"],
        ["OD-14", "Confluent encryption keys per group", "Provider-managed; self-managed key in Azure Key Vault", "Provider-managed for NP1; per key policy for cc-prd and for cc-np2 if it holds production data; Dedicated or a key-only vault for Enterprise (Section 9.5)", "Security architect", "M2, before any cluster is created"],
        ["OD-15", "Data class of PERF and PREPROD", "Masked; unmasked production", "Mask both", "Data security officer", "M2"],
        ["OD-16", "Retention of Pega topics", "Confluent default; shorter; longer", "7 days unless policy needs less; never below the longest outage to survive", "Kafka team, data security officer", "M2"],
        ["OD-17", "Broken item retention and the approved list of indexed properties", "Per application", "Resolve or delete broken items within 30 days; indexed property list signed by the data owner", "Application owner", "M3"],
        ["OD-18", "Encryption at host and disk keys for AKS node pools", "Platform keys; customer key", "Encryption at host on every pool; customer key per the key policy", "Platform team", "M2, before any node pool is created"],
    ], caption="Open decisions", widths=[1.3, 3, 3.6, 4.6, 2.2, 1.9], size=8)
    b.h2("Assumptions")
    b.table(["ID", "Assumption", "Check that would prove it wrong"], [
        ["AS-01", "The customer's Okta tenant includes API Access Management", "Okta admin console shows no custom authorization servers"],
        ["AS-02", "Confluent Cloud offers Enterprise and Dedicated with Private Link in the AKS region", "Confluent console region list"],
        ["AS-03", "The application does not need Cassandra (no Customer Decision Hub or Process AI)", "Application stack review"],
        ["AS-04", "The database engine and version of the clone are on the 26.1.1 Platform Support Guide [R1]", "DBA check against [R1]"],
        ["AS-05", "8.8 queues can be drained within the planned window", "Rehearsal drain time"],
        ["AS-06", "Non-production environments have their own AKS namespaces and network policies", "Platform design review"],
        ["AS-07", "The firewall supports FQDN rules for `<okta-domain>`", "Firewall policy test"],
        ["AS-08", "The AKS clusters were created with a network policy engine, so NetworkPolicy objects are enforced", "A test pod reaches a target that a policy denies"],
        ["AS-09", "The Azure region offers three availability zones for the node sizes chosen", "Node pool creation with zones 1, 2 and 3 fails"],
        ["AS-10", "Production request logs or Pega PDC data are available to build the workload model", "No usable 8.8 usage data"],
        ["AS-11", "The AKS region and the chosen VM sizes support encryption at host [R78]", "Node pool creation with `--enable-encryption-at-host` fails"],
        ["AS-12", "The chosen OpenSearch provider encrypts data and snapshots at rest and enforces HTTPS", "Provider documentation or contract says otherwise"],
    ], caption="Assumptions", widths=[1.4, 7.6, 7.6], size=9)
    b.h2("Source reconciliation")
    b.p("These are the places where sources disagree or leave a gap, with the action taken.")
    b.table(["ID", "Topic", "What the sources say", "Action"], [
        ["RC-01", "SRS version", "The '26 page lists SRS 1.44.3 or later and OpenSearch best practice 2.15 [R14]; the chart README lists a newer SRS and OpenSearch 2.19 [R24]", "Choose OpenSearch 2.15 or 2.19; use the SRS tag the README lists for chart 4.13.0"],
        ["RC-02", "Kafka SASL mechanisms", "Pega lists JAAS, OAUTHBEARER, PLAIN and SCRAM [R11]; the chart's saslMechanism lists PLAIN and SCRAM [R23]", "Use PLAIN (OD-10)"],
        ["RC-03", "Broker settings on Confluent Cloud", "Pega lists replica.fetch.* and unclean.leader.election.enable [R11]; not editable on Confluent Cloud [R34]", "Written confirmation from Confluent; topic max.message.bytes set"],
        ["RC-04", "Kafka version", "The chart's Kafka requirements page names an older Kafka [R26]; the '26 page names client 4.0.0 [R3]", "Follow the '26 page"],
        ["RC-05", "Default customerDeploymentId", "Pega page: generated automatically by the chart [R14]; README: defaults to the namespace name [R23]", "Always set it explicitly"],
        ["RC-06", "Hazelcast removal for a cloned database", "Removal required before updating to '25 [R5]; steps assume a running system [R6]", "GQ-03 to Pega Support"],
        ["RC-07", "DSS and Helm precedence", "Not settled by the pages read", "FS-24; GQ-05"],
        ["RC-08", "SRS checks on issuer and audience", "Pega documents the signature and guid checks only [R23]", "FS-12 in DEV"],
        ["RC-09", "Okta app attributes in client credentials tokens", "Expression language lists app attributes [R46]; client credentials page does not mention them [R43]", "DEV test before choosing option 2"],
        ["RC-10", "SRS replicas in test environments", "Pega sizing: 1 SRS for testing and development [R14]; SRS chart README: minimum 2, best practice 3 [R24]", "2 in DEV, SIT and UAT; 3 elsewhere"],
        ["RC-11", "SRS pod resources", "Pega sizing: 2 CPU, 2 GB [R14]; chart defaults: 0.65 to 1.3 CPU, 4Gi [R24]", "Request 1 CPU, limit 2 CPU, 4Gi; adjust from PERF"],
        ["RC-12", "Topology spread for Pega tiers", "Read by the chart 4.13.0 template [R61]; not in the README [R23]", "Use it; check in `helm template` output after each chart upgrade"],
        ["RC-13", "OpenSearch storage and shard sizing", "Pega gives node sizes only [R14]; general OpenSearch guidance gives formulas [R54, R55]", "Use the formulas with measured index sizes (Section 7.4)"],
    ], caption="Source reconciliation register", widths=[1.3, 3.2, 7.4, 4.7], size=8)
