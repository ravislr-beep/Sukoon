"""Sections 13 to 23: deployment, cutover, rollback, testing, troubleshooting, operations, governance."""
from content_a import GEN, PUB, OWN


def s13_deploy(b):
    b.h1("Deployment runbook")
    b.p("This section builds each environment in the same order. Every step has a verification and an evidence item, so a "
        "reviewer can confirm the environment was built as designed. Values in angle brackets come from Appendix A.")
    b.figure(GEN + "fig_migration_workstreams.png", "Workstreams and dependencies", OWN, width_cm=16)
    b.h2("Build order")
    b.table(["Phase", "Component", "Depends on", "Owner"], [
        ["1", "Azure landing zone: VNet, subnets, firewall routes, private DNS zones, Key Vault, ACR", "Customer landing zone", "Platform team"],
        ["2", "AKS cluster, node pools, External Secrets Operator, monitoring agents", "Phase 1", "Platform team"],
        ["3", "Confluent network, cluster, private endpoints, DNS, service account, ACLs", "Phase 1", "Kafka engineer"],
        ["4", "Search cluster, private connectivity, cluster settings, SRS user", "Phase 1", "Search engineer"],
        ["5", "SRS deployment (backingservices chart)", "Phases 2 and 4; OAuth client (OD-16)", "Search engineer"],
        ["6", "Pega database and installer job; Pega tiers (pega chart)", "Phases 2, 3 and 5", "Pega LSA and platform team"],
        ["7", "Ingress, certificates, public DNS (switched at cutover)", "Phase 6", "Platform team"],
    ], widths=[1.4, 8, 4.4, 2.8], caption="Build order", size=9)
    b.h2("Azure foundation and AKS")
    b.table(["ID", "Action", "Verification", "Evidence"], [
        ["A-1", "Create the spoke VNet and subnets (Section 6.3); peer with the hub; route 0.0.0.0/0 to the firewall.", "Effective routes on the node NIC show the firewall next hop.", "Route table export"],
        ["A-2", "Create private DNS zones and links (Section 6.3.2).", "Resolution test from a VM in the spoke.", "nslookup output"],
        ["A-3", "Create Key Vault (RBAC model, private endpoint, public access disabled) and ACR (private endpoint).", "Access from the spoke works; from the internet is refused.", "Test output"],
        ["A-4", "Create the private AKS cluster with Azure CNI, workload identity and OIDC issuer enabled; system, pega and srs node pools across three zones.", "kubectl get nodes -L topology.kubernetes.io/zone shows three zones.", "Command output"],
        ["A-5", "Grant the kubelet identity AcrPull on ACR.", "A test pod pulls a Pega image.", "Pod event log"],
        ["A-6", "Install External Secrets Operator; create the workload identity federated credential and grant Key Vault Secrets User.", "An ExternalSecret reaches status SecretSynced.", "kubectl describe output"],
        ["A-7", "Install the ingress controller for Application Gateway; create the WAF policy.", "Health probe of a test service is healthy.", "Portal screenshot"],
        ["A-8", "Create namespaces pega-<env>, srs-<env>, platform-ops; apply network policies (deny by default; allow pega to srs, srs to search endpoint, pods to DNS).", "Policy test pod cannot reach a denied target.", "Test output"],
    ], widths=[1.1, 7.8, 5, 2.7], caption="Azure foundation steps", size=8.5)
    b.h2("Confluent Cloud")
    b.table(["ID", "Action", "Verification", "Evidence"], [
        ["C-1", "Create the Confluent environment and network in the AKS region; create the cluster (type per OD-05).", "Cluster status Up in the console.", "Cluster ID"],
        ["C-2", "Complete N-1 to N-6 (Section 7.4).", "V-K-01 passes.", "Command output"],
        ["C-3", "Create a service account per Pega environment and one API key for it; store the JAAS string in Key Vault.", "Key Vault secret version exists; no key in any file or ticket.", "Secret metadata"],
        ["C-4", "Create the ACLs (Section 7.5.2).", "V-K-02 passes.", "ACL export"],
        ["C-5", "Agree the partition budget (Section 7.6) and confirm the cluster capacity.", "Budget recorded in Appendix A.", "Calculation"],
        ["C-6", "Enable audit logs and metrics export (Section 18).", "Metrics visible in the monitoring workspace.", "Screenshot"],
    ], widths=[1.1, 7.8, 5, 2.7], caption="Confluent Cloud steps", size=8.5)
    b.h2("Search cluster and SRS")
    b.table(["ID", "Action", "Verification", "Evidence"], [
        ["S-1", "Provision the search cluster per OD-04 with three cluster-manager and three or more data nodes across zones.", "V-S-01 passes.", "Output"],
        ["S-2", "Enable private connectivity and DNS for the search endpoint.", "Resolution and TLS test from a pod in srs-<env>.", "Output"],
        ["S-3", "Create the SRS user. Grant the manage cluster privilege, or apply the settings in Section 8.5 manually.", "V-S-02 passes.", "Output"],
        ["S-4", "Register the OAuth client for Pega (private_key_jwt preferred) and record the token endpoint and public key URL.", "V-S-06 passes.", "Decoded claims"],
        ["S-5", "Create the Key Vault secrets and ExternalSecrets for srs-search-credentials, srs-runtime-certs and pega-srs-oauth.", "Kubernetes secrets exist.", "kubectl output"],
        ["S-6", "Deploy SRS: helm upgrade --install srs-<env> pega/backingservices -n srs-<env> -f backingservices-<env>.yaml.", "V-S-03 and V-S-04 pass.", "Output"],
    ], widths=[1.1, 7.8, 5, 2.7], caption="Search and SRS steps", size=8.5)
    b.h2("Pega")
    b.table(["ID", "Action", "Verification", "Evidence"], [
        ["G-1", "Prepare values-<env>.yaml from Appendix B: provider aks, images, jdbc with external secret, stream, pegasearch, customerDeploymentId, tiers, ingress, hpa, pdb.", "Peer review against Appendix A.", "Reviewed values file"],
        ["G-2", "Add the Pega Helm repository: helm repo add pega https://pegasystems.github.io/pega-helm-charts; pin the chart version.", "helm search repo pega shows the pinned version.", "Output"],
        ["G-3", "Run the installer action (install for a new environment, upgrade for a migrated database).", "Installer job completes successfully.", "Job log"],
        ["G-4", "Deploy the tiers (global.actions.execute deploy).", "All pods Ready; P-1.", "Output"],
        ["G-5", "Log in as administrator; check the Stream landing page.", "V-K-06 passes.", "Screenshot"],
        ["G-6", "Check queue processors and search status.", "V-K-09 and V-S-08 pass.", "Screenshots"],
        ["G-7", "Run the smoke test pack (Section 16).", "All smoke tests pass.", "Test report"],
    ], widths=[1.1, 7.8, 5, 2.7], caption="Pega deployment steps", size=8.5)
    b.h2("Promotion across environments")
    b.bullets([
        "Keep values files, ExternalSecret manifests, Confluent ACL scripts and search settings in Git. Every change goes through review.",
        "Build environments in order: development, test, staging, production. Do not change a setting in production that was not first applied in staging.",
        "Pin the Pega Helm chart version and image digests per release. Record them in Appendix A.",
        "Each environment has its own topic prefix, service account, customerDeploymentId and OAuth client.",
    ])


def s14_cutover(b):
    b.h1("Cutover runbook")
    b.p("This section describes the Release 2 cutover in detail, because it has the longest outage. Release 1 follows the "
        "sequence in Section 10.5 and Release 3 the sequence in Section 10.7; both use the same Go/No-Go structure.")
    b.h2("Go/No-Go criteria")
    b.table(["Gate", "When", "Criteria", "Decision owner"], [
        ["Go/No-Go 1", "Seven days before", "Two successful rehearsals on staging with production-scale data; durations fit the window with at least 25 % contingency; all V-K and V-S checks passed in rehearsal; rollback rehearsed; open defects accepted", "Business owner with platform lead"],
        ["Go/No-Go 2", "After smoke tests, before DNS switch", "V-K-06, V-K-09, V-S-08, V-S-09 pass; smoke tests pass; Hazelcast checks H-6 and H-7 pass", "Cutover manager"],
        ["Go/No-Go 3", "30 minutes after DNS switch", "No priority 1 or 2 incidents; error rate and response times within agreed limits; queue backlog falling", "Cutover manager with business owner"],
    ], widths=[2.4, 3, 8.4, 2.8], caption="Go/No-Go gates", size=9)
    b.h2("Release 2 cutover sequence")
    b.figure(GEN + "fig_cutover_flow.png", "Release 2 cutover sequence", OWN, width_cm=8.8)
    b.table(["Step", "Action", "Owner", "Duration source", "Evidence"], [
        ["T-1", "Confirm Go/No-Go 1 record; confirm backups and support contacts (Pega, Confluent, search provider, Azure).", "Cutover manager", "Fixed", "Signed record"],
        ["T-2", "Start change freeze on 8.8; publish the outage notice.", "Business owner", "Fixed", "Notice"],
        ["T-3", "Stop producers (K-E2).", "Pega LSA", "Rehearsal", "Screenshot"],
        ["T-4", "Drain with the Stream Migration activity (K-E3, K-E4).", "Pega LSA", "Rehearsal", "JSON responses (V-K-04)"],
        ["T-5", "Stop all 8.8 nodes; take the final database backup.", "Platform team, DBA", "Rehearsal", "Backup ID"],
        ["T-6", "Restore the backup to the Azure database.", "DBA", "Rehearsal", "Restore log"],
        ["T-7", "Run the bridge installer job (upgrade, in-place).", "Platform team", "Rehearsal", "Job log"],
        ["T-8", "Deploy the bridge tiers with the new prefix and customerDeploymentId.", "Platform team", "Rehearsal", "Pods Ready"],
        ["T-9", "Remove Hazelcast (H-1 to H-7).", "Pega LSA", "Rehearsal", "API responses"],
        ["T-10", "Full index build; V-S-07 to V-S-09.", "Pega LSA", "Rehearsal", "Screenshots, comparison sheet"],
        ["T-11", "Smoke tests; Go/No-Go 2.", "Test lead", "Rehearsal", "Test report, gate record"],
        ["T-12", "Switch public DNS to Application Gateway; re-enable producers.", "Platform team", "DNS TTL", "DNS change record"],
        ["T-13", "Go/No-Go 3; start hypercare.", "Cutover manager", "30 minutes", "Gate record"],
    ], widths=[1.1, 7.2, 2.7, 2.4, 3.2], caption="Release 2 cutover steps", size=8.5)
    b.callout("important", "Lower the TTL of the public DNS record to 300 seconds at least 48 hours before cutover so that a DNS switch or revert takes effect quickly. Restore the normal TTL after hypercare.")
    b.h2("Communication")
    b.table(["When", "Audience", "Message", "Channel"], [
        ["14 days before", "Business users", "Outage window and expected effect", "Email and intranet"],
        ["1 day before", "Support teams and vendors", "Contacts, bridge call details, escalation path", "Email"],
        ["Each gate", "Steering group", "Gate result and next step", "Bridge call and chat"],
        ["Go-live", "Business users", "Service available; how to report issues", "Email"],
    ], widths=[2.4, 4, 6.4, 3.8], caption="Communication plan", size=9)


def s15_rollback(b):
    b.h1("Rollback")
    b.h2("Principles")
    b.bullets([
        "Each release keeps the previous state intact until its rollback window closes: 8.8 topics and indexes in Releases 1 and 2, the 8.8 database and servers in Release 2, the pre-update backup and old rules schema in Release 3.",
        "Rollback is simplest before users work on the new state. After that, data entered on the new state must be reconciled or re-keyed, so the business owner decides between rollback and fixing forward.",
        "The rollback window and point of no return for each release are agreed at Go/No-Go 1 (OD-10).",
    ])
    b.h2("Release 1 rollback")
    b.table(["Situation", "Action", "Data effect"], [
        ["Before traffic is re-opened", "Stop nodes; restore the previous stream and search configuration; start nodes.", "None: queues were drained and no new work was created."],
        ["After traffic is re-opened", "Prefer fixing forward. A move from Confluent back to the 8.8 embedded stream is not a documented Pega path; if the business still decides to revert, drain with the Stream Migration activity first and accept the risk in writing.", "Messages produced to Confluent must be drained first; searches use the old indexes, which miss changes made after the switch until reindexed."],
    ], widths=[3.6, 7.6, 5.4], caption="Release 1 rollback", size=9)
    b.h2("Release 2 rollback")
    b.figure(GEN + "fig_rollback_tree.png", "Decision: Release 2 rollback", OWN, width_cm=13)
    b.table(["Step", "Action"], [
        ["RB-1", "Declare rollback and record the reason and time."],
        ["RB-2", "Stop producers on the target. If users worked on the target, export the list of cases created or changed since cutover (reconciliation report)."],
        ["RB-3", "Revert public DNS to the 8.8 entry point."],
        ["RB-4", "Start the 8.8 nodes on the original database. Their topics (old prefix) and indexes (old customerDeploymentId) were not touched."],
        ["RB-5", "Check the 8.8 Stream landing page (Provider ExternalKafka, Status NORMAL) and search status."],
        ["RB-6", "Re-open 8.8 to users; scale the target to zero but keep it for analysis."],
    ], widths=[1.4, 15.2], caption="Release 2 rollback steps", size=9)
    b.h2("Release 3 rollback")
    b.p("The zero-downtime update upgrades the data schema in place after the rules move to the new rules schema [R28]. "
        "Rolling back therefore needs the pre-update database backup. Take a full backup immediately before U-7, keep the old "
        "rules schema until acceptance, and redeploy the bridge images against the restored database if a rollback is declared. "
        "Work done on 26.1.1 after the update is lost on rollback unless re-keyed, so the business owner makes this decision.")


def s16_testing(b):
    b.h1("Testing and acceptance")
    b.h2("Test stages")
    b.table(["Stage", "Purpose", "Examples", "Environment"], [
        ["Connectivity", "Prove every network and security hop", "V-K-01 to V-K-03, V-S-01 to V-S-06", "Every environment"],
        ["Component", "Each service works on its own", "Produce and consume with kcat; SRS health; index create through SRS", "Development"],
        ["Integration", "Pega uses Kafka and search correctly", "Queue processor test item; job scheduler run; case search; report on indexed data", "Test"],
        ["Application regression", "Business functions unchanged", "PegaUnit test suites; automated UI and API tests; manual scripts", "Test, staging"],
        ["Performance", "Throughput and response time at peak load", "Peak user load plus queue processor load; index build throughput", "Staging"],
        ["Resilience", "Behavior when a component fails", "See Section 16.4", "Staging"],
        ["Security", "Controls work as designed", "No public endpoints; secret scanning of values files; token claim checks; TLS versions", "Test, staging"],
        ["Migration rehearsal", "Measure and prove the cutover", "Full Release 1, 2 or 3 run with timing", "Staging"],
        ["User acceptance", "Business sign-off", "Business scenarios including search", "Staging"],
        ["Operational acceptance", "Run the service", "Alerts fire and reach on-call; runbooks used by operations staff", "Staging"],
    ], widths=[3, 4.2, 6.4, 3], caption="Test stages", size=8.5)
    b.h2("Rehearsals")
    b.p("Plan at least two rehearsals for each release: a technical rehearsal to prove the steps, and a dress rehearsal "
        "run by the people who will do the production cutover, against production-scale data (OD-13). Record these "
        "measurements, because they set the outage window:")
    b.table(["Measurement", "Steps", "Used for"], [
        ["Drain duration", "K-E3 to K-E4", "Window; producer stop time"],
        ["Database backup, transfer and restore", "T-5 to T-6", "Window; database copy method (OD-17)"],
        ["Installer job duration", "T-7, U-7", "Window"],
        ["Hazelcast removal", "H-1 to H-7", "Window"],
        ["Full index build", "S-E4 to S-E6", "Window; search sizing"],
        ["Smoke test duration", "T-11", "Window"],
        ["Partition count after start", "K-5", "Confluent capacity"],
    ], widths=[5, 4, 7.6], caption="Rehearsal measurements", size=9)
    b.h2("Pega unit and integration tests")
    b.bullets([
        "Run the application's PegaUnit test suites after each release in test and staging; record pass rates against the 8.8 baseline.",
        "Add a platform test case that queues an item to a test queue processor and asserts it is processed; run it after every deployment.",
        "Add a search test case that creates a case, waits for indexing, and searches for it.",
        "For each Kafka data set, run its data flow in test and compare record counts with the source.",
    ])
    b.h2("Resilience tests")
    b.table(["Test", "Method", "Expected behavior"], [
        ["Batch pod loss", "Delete one batch pod during queue processing", "Pod is recreated; queue processing continues; no items lost"],
        ["Web pod loss", "Delete one web pod under load", "Users on other pods unaffected; affected users re-authenticate"],
        ["Zone loss (simulated)", "Cordon and drain all nodes in one zone", "Pods reschedule in other zones within PDB limits"],
        ["SRS pod loss", "Delete one SRS pod", "Searches continue on remaining replicas"],
        ["Search node restart", "Restart one data node (provider tooling)", "Cluster yellow then green; searches continue"],
        ["Secret rotation", "Rotate the Confluent API key (Section 9.1)", "No processing gap beyond the rolling restart"],
    ], widths=[3.2, 6, 7.4], caption="Resilience tests", size=9)
    b.h2("Acceptance criteria")
    b.table(["ID", "Criterion"], [
        ["AC-1", "All validation checks in Sections 11.5 and 12.5 pass in production, with evidence filed."],
        ["AC-2", "Application regression pass rate equal to or better than the 8.8 baseline; no open priority 1 or 2 defects."],
        ["AC-3", "Performance results within the targets agreed by the business owner."],
        ["AC-4", "Resilience tests pass in staging."],
        ["AC-5", "Monitoring and alerts in Section 18 are live and tested."],
        ["AC-6", "Operations staff have run the routine procedures in Section 18.3 in staging."],
    ], widths=[1.4, 15.2], caption="Acceptance criteria", size=9)


def s17_troubleshooting(b):
    b.h1("Troubleshooting")
    b.h2("Method")
    b.p("Most failures between Pega and Kafka or search are connectivity failures. Work through the chain in {ref:fig_chain} in "
        "order; a failure at one step makes every later step fail, so the first failing step is the one to fix. Commands are "
        "in Appendix D.")
    b.figure(GEN + "fig_connectivity_chain.png", "Connectivity chain for Kafka and search", OWN, width_cm=16, label="chain")
    b.h2("Kafka")
    b.figure(GEN + "fig_troubleshoot_kafka.png", "Troubleshooting tree: stream service", OWN, width_cm=14)
    b.table(["Symptom", "Likely cause", "Check", "Fix"], [
        ["Stream landing page status not NORMAL after start", "Bootstrap unreachable or authentication failure", "K-1 to K-3; Pega log for SASL errors", "Fix DNS or network; correct the JAAS secret and restart"],
        ["Connects to bootstrap, then broker timeouts", "Zonal broker DNS records missing", "Resolve each broker name from K-3", "Add the zonal records Confluent lists [R38]"],
        ["TopicAuthorizationException or GroupAuthorizationException", "ACL prefix does not match streamNamePattern", "Compare V-K-07 output with ACLs", "Correct the prefix or add the ACL"],
        ["Transactional or idempotent producer errors", "Missing TRANSACTIONAL_ID or IDEMPOTENT_WRITE ACL; Freight cluster", "ACL list; cluster type", "Add ACLs; use Enterprise or Dedicated [R37]"],
        ["RecordTooLargeException", "Topic max.message.bytes below the message size", "K-6", "Raise to 5,000,000; align JVM arguments if larger [R13]"],
        ["Queue processors stuck with Ready to process growing", "Batch tier down, or consumers failing", "Admin Studio; batch pod logs", "Restore batch pods; fix the failing processor"],
        ["Slow client-broker communication after Release 3", "Client and broker compatibility", "Pega log; Confluent support", "Confirm the Confluent version supports the 4.0.0 client [R3]"],
        ["Stream Migration activity never reaches COMPLETED", "Items in STOPPED, FAILED or broken state; producers still active", "Admin Studio; data flow status", "Stop producers; restart or resolve stuck processors; poll again [R15]"],
    ], widths=[3.8, 3.8, 3.8, 5.2], caption="Kafka symptoms", size=8.5)
    b.h2("Search")
    b.figure(GEN + "fig_troubleshoot_search.png", "Troubleshooting tree: search", OWN, width_cm=14)
    b.table(["Symptom", "Likely cause", "Check", "Fix"], [
        ["SRS pods not Ready", "Search cluster unreachable or wrong credentials", "SRS logs; S-1 from an SRS pod", "Fix network or authSecret; restart SRS"],
        ["Pega search returns errors with 401 or 403 in SRS logs", "Token missing scope or guid; wrong public key URL", "Decode a token (V-S-06)", "Fix the IdP claims (OD-16) or OAuthPublicKeyURL"],
        ["Index creation fails", "Index auto-creation or permissions", "S-3; SRS user privileges", "Apply Section 8.5 settings; grant privileges"],
        ["Index deletion fails on Elasticsearch 8", "destructive_requires_name true", "S-3", "Set it to false [R16]"],
        ["Results missing for recent changes", "Incremental indexing backlog", "Queue processor landing page", "Clear the backlog; check batch capacity"],
        ["Class status CONFLICTS FOUND", "Mapping conflicts in indexed properties", "Search landing page [R21]", "Analyze and fix the conflicting properties; reindex the class"],
        ["Cluster status red", "Lost data node or disk watermark", "S-2; provider console", "Restore capacity; follow provider guidance"],
    ], widths=[3.8, 3.8, 3.8, 5.2], caption="Search symptoms", size=8.5)
    b.h2("Upgrade and Hazelcast removal")
    b.table(["Symptom", "Likely cause", "Fix"], [
        ["primaryKeyUtility reports insufficient database space", "The utility copies each table missing a primary key", "Increase database storage and rerun [R12]"],
        ["ClassNotFoundException for javax.* classes after Release 3", "Custom JAR not rebuilt for Jakarta EE", "Import the updated JAR into a higher CodeSet version and restart [R11]"],
        ["checkRemoteExecutionConnectivity does not return allNodesReachable", "Nodes cannot exchange messages through Kafka", "Check the stream service and topic ACLs; rerun [R7]"],
        ["Installer job fails", "Database connectivity, permissions or schema names", "Read the job log (P-5); correct values; rerun"],
    ], widths=[5, 5, 6.6], caption="Upgrade symptoms", size=8.5)
    b.h2("Support cases")
    b.p("Pega Global Client Support handles issues in externalized services with the same model as for databases and "
        "application servers: basic troubleshooting to determine the cause, then a handover to the third-party provider if the "
        "issue is not in Pega software [R24]. Open cases with this evidence: Pega logs from all tiers for the period, Stream "
        "landing page screenshot, queue processor status, SRS logs, the relevant Appendix D outputs, and the Helm values with "
        "secrets removed.")


def s18_ops(b):
    b.h1("Observability and operations")
    b.h2("Monitoring design")
    b.figure(GEN + "fig_observability.png", "Telemetry flows", OWN, width_cm=16)
    b.h2("Signals and alerts")
    b.table(["Signal", "Source", "Alert when", "First action"], [
        ["Stream service status", "Pega (Stream landing page, PDC)", "Not NORMAL", "Section 17.2"],
        ["Queue processor backlog", "Pega Admin Studio, PDC", "Ready to process grows for longer than the agreed period", "Check batch tier and consumer errors"],
        ["Broken queue items", "Pega", "Above zero for business-critical processors", "Investigate and requeue"],
        ["Confluent consumer lag and request errors", "Confluent Metrics API", "Lag above baseline; authentication or authorization errors", "Section 17.2"],
        ["Confluent partition count", "Confluent Metrics API", "Above 70 % of the cluster limit", "Plan capacity (Section 7.6)"],
        ["SRS errors and latency", "SRS logs and metrics", "Error rate or latency above baseline", "Section 17.3"],
        ["Search cluster health and disk", "Provider metrics", "Status yellow for longer than the agreed period, red at once; disk above watermark warning", "Section 17.3"],
        ["Pod restarts and readiness", "Container Insights", "Restart loops; pods not Ready", "kubectl describe; logs"],
        ["Certificate expiry", "Synthetic checks", "Less than 30 days to expiry", "Renew (Section 9.2)"],
        ["Private endpoint DNS", "Synthetic checks", "Resolution returns a public IP or fails", "Section 6.3.2"],
    ], widths=[3.6, 3.4, 5.4, 4.2], caption="Signals and alerts", size=8.5)
    b.h2("Routine operations")
    b.table(["Task", "Frequency", "Owner", "Procedure"], [
        ["Check new Pega topics for max.message.bytes", "After each deployment", "Kafka engineer", "K-4, K-6"],
        ["Rotate Confluent API keys", "Per security policy", "Kafka engineer", "Section 9.1"],
        ["Rotate search credentials", "Quarterly", "Search engineer", "Update Key Vault; restart SRS"],
        ["Renew certificates", "Before expiry", "Platform team", "Section 9.2"],
        ["Review partition and storage growth", "Monthly", "Kafka and search engineers", "K-5; S-4"],
        ["Apply Pega patches", "Per Pega maintenance program", "Pega LSA", "Zero-downtime patch [R28]"],
        ["Update SRS", "With Pega updates or security fixes", "Search engineer", "Section 8.6"],
        ["Upgrade AKS", "Per AKS support calendar", "Platform team", "Node pool surge upgrade with PDBs"],
        ["Delete retired topics and indexes", "After each rollback window", "Kafka and search engineers", "V-K-12, V-S-12"],
    ], widths=[5.4, 3.6, 3.4, 4.2], caption="Routine operations", size=8.5)


def s19_dr(b):
    b.h1("Resilience and disaster recovery")
    b.p("Within the primary region, every layer runs across three availability zones: AKS node pools, the Confluent cluster, "
        "the search cluster and the database. The disaster recovery design for a region loss is an open decision (OD-12). "
        "The points below apply whichever option is chosen.")
    b.table(["Layer", "Regional loss behavior", "Design point"], [
        ["Pega tiers", "Redeploy in the DR region from Git and ACR (geo-replicated)", "Keep DR values files current; test yearly"],
        ["Database", "Recover from geo-replica or geo-backup", "RPO and RTO set by the database option"],
        ["Kafka", "Stream data in flight in the lost region is not recoverable through Pega; the DR cluster starts with empty Pega topics, the same principle as in migration [R15]", "Pre-create the DR Confluent cluster, network and ACLs; accept loss of in-flight queue items, or keep them recoverable from the database"],
        ["Search", "Rebuild indexes in DR from the database", "Plan the rebuild time in the RTO; or use the provider's cross-region replication if offered"],
        ["Secrets", "Key Vault in DR region with replicated secrets", "Separate Confluent service account and OAuth client for DR"],
    ], widths=[2.6, 7, 7], caption="Regional disaster recovery points", size=9)


def s20_raci(b):
    b.h1("Roles and responsibilities")
    b.p("R = responsible, A = accountable, C = consulted, I = informed.")
    b.table(["Activity", "Business owner", "Enterprise architect", "Security", "Platform team", "Pega LSA", "Kafka engineer", "Search engineer", "Test lead"], [
        ["Approve design and open decisions", "A", "R", "C", "C", "C", "C", "C", "I"],
        ["Azure foundation and AKS", "I", "C", "C", "A/R", "I", "I", "I", "I"],
        ["Confluent Cloud", "I", "C", "C", "C", "C", "A/R", "I", "I"],
        ["Search cluster and SRS", "I", "C", "C", "C", "C", "I", "A/R", "I"],
        ["Pega configuration and update", "I", "C", "I", "R", "A/R", "C", "C", "I"],
        ["Kafka topic migration", "I", "I", "I", "C", "A/R", "R", "I", "C"],
        ["Search index migration", "I", "I", "I", "C", "A/R", "I", "R", "C"],
        ["Testing and rehearsals", "C", "I", "C", "R", "R", "R", "R", "A"],
        ["Cutover and rollback decisions", "A", "C", "I", "R", "R", "R", "R", "C"],
        ["Operations after handover", "I", "I", "C", "A/R", "R", "R", "R", "I"],
    ], widths=[4.4, 1.6, 1.6, 1.4, 1.6, 1.4, 1.6, 1.6, 1.4], caption="RACI", size=8)


def s21_risks(b):
    b.h1("Risks")
    b.table(["ID", "Risk", "L", "I", "Mitigation", "Owner"], [
        ["RK-01", "The bridge-to-26.1.1 path is not confirmed for the chosen bridge patch", "M", "H", "OD-02: confirm with Pega Support before Release 2 design freeze", "Pega LSA"],
        ["RK-02", "8.8 servers cannot reach Confluent and SRS privately for Release 1", "M", "H", "Network design early; fallback is the combined option after Pega Support confirmation", "Platform team"],
        ["RK-03", "Index build longer than the outage window", "M", "H", "Measure in rehearsal; scale search data nodes and SRS for the build; tune maxrecords DSS", "Search engineer"],
        ["RK-04", "Drain does not complete because of stuck or broken items", "M", "M", "Resolve broken items before cutover; producer stop checklist; time-box with a Go/No-Go decision", "Pega LSA"],
        ["RK-05", "Identity provider cannot issue the claims SRS checks", "M", "H", "OD-16: prove in the first environment; choose another provider if needed", "Security"],
        ["RK-06", "Partition limit reached on Confluent Enterprise", "L", "M", "Measured budget; Dedicated if needed", "Kafka engineer"],
        ["RK-07", "Messages larger than the topic limit after Pega creates new topics", "M", "M", "Post-deployment topic check (V-K-08); alert", "Kafka engineer"],
        ["RK-08", "Custom JARs fail on Jakarta EE", "M", "H", "Upgrade Tools report early; rebuild and test in Release 3 rehearsal", "Pega LSA"],
        ["RK-09", "Tables without primary keys block the update", "M", "H", "Dry run in preparation; fix before Release 3", "DBA"],
        ["RK-10", "Behavior change in queue processing on '26", "M", "M", "Custom queue processor tests (P-6); performance test", "Pega LSA"],
        ["RK-11", "Rehearsal data not representative", "M", "H", "OD-13: production-scale masked or synthetic data", "Test lead"],
        ["RK-12", "Vendor documentation changes between rehearsal and release", "M", "M", "Recheck Section 3 facts before each release", "Enterprise architect"],
    ], widths=[1.3, 5.4, 0.7, 0.7, 6.2, 2.3], caption="Risk register (L likelihood, I impact: H high, M medium, L low)", size=8.5)


def s22_open(b):
    b.h1("Open decisions")
    b.p("The draft runbook used OD-01 to OD-15. This register replaces that list for Kafka, search and the upgrade path.")
    b.table(["ID", "Decision", "Options", "Recommendation", "Owner", "Needed by"], [
        ["OD-01", "Source estate facts", "Collect per Section 4.1", "Complete the assessment", "Pega LSA", "Design start"],
        ["OD-02", "Bridge release patch", "Latest '24.1 (24.1.4+); latest '24.2 (24.2.3+)", "Latest '24.1, confirmed with Pega Support", "Pega LSA", "Release 2 design"],
        ["OD-03", "Delivery option", "Three releases; combined Release 1 and 2", "Three releases", "Business owner", "Plan approval"],
        ["OD-04", "Search provider", "Elastic Cloud on Azure; managed OpenSearch provider on Azure; self-managed OpenSearch", "Managed service that passes the Section 8.3 checks", "Enterprise architect", "Release 1 design"],
        ["OD-05", "Confluent cluster type", "Enterprise; Dedicated", "Enterprise unless partition budget or networking needs Dedicated", "Kafka engineer", "Release 1 design"],
        ["OD-06", "Kafka authentication", "SASL/PLAIN API key; SASL/OAUTHBEARER", "PLAIN; review OAUTHBEARER after go-live", "Security", "Release 1 design"],
        ["OD-07", "Topic creation", "Pega creates (CREATE ACL); pre-created topics", "Pega creates", "Security", "Release 1 design"],
        ["OD-08", "Application Kafka data sets", "Keep; new only; Cluster Linking; replay", "Per data set (Section 11.4.1)", "Application owner", "Release 2 design"],
        ["OD-09", "Outage windows", "Per release", "From rehearsal plus 25 %", "Business owner", "Go/No-Go 1"],
        ["OD-10", "Rollback windows and points of no return", "Per release", "Agree at Go/No-Go 1", "Business owner", "Go/No-Go 1"],
        ["OD-11", "Index strategy in Release 2", "New customerDeploymentId with full build; reuse", "New ID with full build", "Pega LSA", "Release 2 rehearsal"],
        ["OD-12", "Disaster recovery", "Warm standby; rebuild in DR", "Business RPO and RTO first", "Enterprise architect", "Release 2 design"],
        ["OD-13", "Rehearsal data", "Masked production; synthetic at scale", "Production-scale, masked", "Business owner", "First rehearsal"],
        ["OD-14", "Monitoring integration", "Azure Monitor; existing tools", "Azure Monitor with SIEM export", "Platform team", "Release 1"],
        ["OD-15", "Third-party support contracts", "Confluent and search provider support levels", "Production support for both", "Business owner", "Release 1"],
        ["OD-16", "Identity provider for Pega to SRS", "Entra ID with custom claims; another OAuth provider", "Provider that issues scope and guid claims", "Security", "First environment"],
        ["OD-17", "Database copy method", "Native backup and restore; replication tool", "Measured in rehearsal", "DBA", "Release 2 rehearsal"],
    ], widths=[1.3, 2.8, 4, 3.8, 2.4, 2.3], caption="Open decisions", size=8)


def s23_reconcile(b):
    b.h1("Source reconciliation register")
    b.p("These are the places where sources disagree, or where an earlier draft or review said something the evidence does "
        "not support. Each entry states the action taken in this document.")
    b.table(["ID", "Topic", "What the sources say", "Action"], [
        ["RC-01", "SRS and search versions", "'26 page: SRS 1.44.3 or later; Elasticsearch up to 8.19.11, best practice 8.18.3; OpenSearch best practice 2.15 [R16]. Helm README: SRS 1.49.2, Elasticsearch up to 8.19.22, OpenSearch 2.19 [R29].", "Choose search versions listed on the '26 page; use the SRS image the README lists for the chart in use; recheck before each release."],
        ["RC-02", "Kafka SASL mechanisms", "Pega page lists JAAS, OAUTHBEARER, PLAIN and SCRAM [R13]; Helm saslMechanism lists PLAIN, SCRAM-SHA-256, SCRAM-SHA-512 [R28].", "Use PLAIN (AD-08). OAUTHBEARER only after a successful rehearsal."],
        ["RC-03", "Kafka version", "KafkaClusterRequirement.md says Apache Kafka 3.4.0 or earlier [R31]; '26 ships client 4.0.0 and supports Kafka server 4.0.0 [R3].", "Follow the '26 documentation."],
        ["RC-04", "Broker settings on Confluent Cloud", "Pega lists replica.fetch.* and unclean.leader.election.enable [R13]; these are not editable on Confluent Cloud [R40].", "Request written confirmation from Confluent; set topic max.message.bytes (V-K-08)."],
        ["RC-05", "SystemPulse partitions", "Hazelcast removal prerequisites: one partition [R6]; '26 prerequisites: six partitions [R3].", "One at the bridge release if pre-creating topics; six for '26."],
        ["RC-06", "Extra partitions for Hazelcast removal", "About 100 per environment; 30 from 25.1.2 or 25.1.1 with HFIX-C4655 [R6].", "Plan 100 for the '24.1 bridge."],
        ["RC-07", "Confluent Private Link on Azure", "The Azure Private Link page describes Dedicated clusters [R38]; Enterprise uses Private Link for serverless products.", "Follow the Confluent page that matches the cluster type chosen in OD-05."],
        ["RC-08", "Hazelcast Clustering Service", "An earlier review of the draft recommended deploying the Hazelcast Clustering Service. Pega removed Hazelcast in '25, including the Clustering Service [R5, R9].", "Withdrawn. Hazelcast is removed in Release 2 and not used on 26.1.1."],
        ["RC-09", "Direct update from 8.8", "The draft assumed one update from 8.8 to 26.1.1. Hazelcast removal tooling needs 23.1.4, 24.1.3, 24.2.2 or later [R9].", "Replaced by the three-release plan (Section 10)."],
        ["RC-10", "Stream Migration activity on 8.8", "The page is published for '25 and '26 and states the activity is in 8.7 and later [R15].", "Prove the REST endpoint on 8.8 in the first Release 1 rehearsal (V-K-04)."],
        ["RC-11", "Default customerDeploymentId", "Pega page: generated automatically by the Helm chart when not specified [R16]; Helm README: defaults to the namespace name [R28].", "Always set it explicitly."],
    ], widths=[1.3, 3, 7.6, 4.7], caption="Reconciliation register", size=8)
