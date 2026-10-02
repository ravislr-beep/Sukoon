"""Sections 12 to 14: deployment runbook, production cutover and rollback, testing."""
from content_a import GEN, PUB, OWN
import envs as E


def _steps_table(b, caption, rows, label=None):
    b.table(["ID", "Action", "Owner", "Check", "Evidence"], rows, caption=caption,
            widths=[1.2, 7, 2.3, 3.6, 2.5], size=8, label=label)


def s12_deploy(b):
    b.h1("Deployment runbook per environment")
    b.p("Every environment is built in the same order, with a check after each step. Shared services are created once per "
        "group (NP1, NP2, PROD); per-environment objects are created for each environment. Values in angle brackets come "
        "from Appendix A, and commands from Appendix C.")
    b.h2("Build order")
    b.table(["Phase", "Component", "Scope", "Depends on", "Owner"], [
        ["1", "Network and DNS: private endpoint subnet, firewall rules, private DNS zones", "Per group and per environment", "Landing zone", "Cloud architect"],
        ["2", "Key Vault, External Secrets Operator identity, Okta authorization server and client", "Per environment", "Phase 1", "Platform team, identity team"],
        ["3", "Confluent cluster and Private Link; service account, ACLs, quota, API key", "Cluster per group; rest per environment", "Phases 1, 2", "Kafka engineer"],
        ["4", "OpenSearch service and private endpoint; cluster settings; SRS user and role", "Service per group; user per environment", "Phases 1, 2", "Search engineer"],
        ["5", "SRS deployment (backingservices chart)", "Per environment", "Phases 2, 4", "Search engineer"],
        ["6", "Database clone, masking, upgrade (run U)", "Per environment", "GQ answers or conservative plan", "DBA team, platform team"],
        ["7", "Clean-up and first start (run F), index build (run D), intake release", "Per environment", "Phases 3, 5, 6", "Pega LSA, platform team"],
    ], caption="Build order", widths=[1.2, 6.4, 3.4, 2.8, 2.8], size=8.5)
    b.h2("Network and DNS")
    _steps_table(b, "Network and DNS steps", [
        ["NW-1", "Create the private endpoint subnet with network policies for private endpoints enabled.", "Cloud architect", "Subnet exists; NSG applies", "Azure export"],
        ["NW-2", "For a new group, complete N-1 to N-6 (Section 6.4) for its Confluent cluster.", "Kafka engineer", "K-1 to K-3 pass from a pod", "Command output"],
        ["NW-3", "For a new group, create the OpenSearch private endpoint and DNS record as the provider documents.", "Search engineer", "S-1 resolves to a private IP and returns the version", "Command output"],
        ["NW-4", "Add firewall rules for this environment: its own Confluent and OpenSearch endpoints, `<okta-domain>:443`, registry and Pega Diagnostic Center if used. Deny production endpoints from non-production.", "Cloud architect", "Allowed tests pass; denied tests fail (IT-09)", "Rule export, test output"],
        ["NW-5", "Apply Kubernetes network policies: deny by default; allow pega to srs, srs to the OpenSearch endpoint, pods to DNS.", "Platform team", "Test pod cannot reach a denied target", "Test output"],
    ])
    b.h2("Secrets and identity")
    _steps_table(b, "Secrets and identity steps", [
        ["SI-1", "Create `kv-pega-<code>` with RBAC, private endpoint and public access disabled.", "Platform team", "Reachable from the spoke only", "Test output"],
        ["SI-2", "Create the workload identity for the External Secrets Operator in `pega-<code>` and `srs-<code>`; grant Key Vault Secrets User on this vault only.", "Platform team", "SecretStore Ready", "kubectl output (P-4)"],
        ["SI-3", "Create the Okta client `pega-srs-<code>` and register its public key (Section 7.6); store the private key in Key Vault.", "Identity team", "Token request succeeds (O-1)", "Decoded claims (O-2)"],
        ["SI-4", "Create the ExternalSecrets in Section 8.2.", "Platform team", "All secrets SecretSynced", "kubectl output"],
    ])
    b.h2("Confluent Cloud")
    _steps_table(b, "Confluent Cloud steps", [
        ["CC-1", "For a new group, create the cluster (type per OD-02) in the AKS region with Private Link.", "Kafka engineer", "Cluster status Up", "Cluster ID"],
        ["CC-2", "Create service account `sa-pega-<code>` and the four ACLs (Section 6.5).", "Kafka engineer", "ACL list matches {ref:tab_acls} (K-7)", "ACL export"],
        ["CC-3", "Create an API key for the service account; write the JAAS value to `kv-pega-<code>` as `confluent-jaas`.", "Kafka engineer", "Secret version exists; key not in any file or ticket", "Secret metadata"],
        ["CC-4", "In NP1 and NP2, create the client quota for the service account (OD-09).", "Kafka engineer", "Quota listed", "Quota export"],
        ["CC-5", "Run IT-01 to IT-04 against the other environments in the group.", "Kafka engineer", "All denied", "Test output"],
    ])
    b.h2("OpenSearch")
    _steps_table(b, "OpenSearch steps", [
        ["OS-1", "For a new group, provision the OpenSearch service (OD-03) at the size in Section 7.4, version 2.15 or 2.19.", "Search engineer", "S-1 shows the version; S-2 green", "Output"],
        ["OS-2", "For a new group, apply the cluster settings in Section 7.4 as administrator.", "Search engineer", "S-3 shows both settings", "Output"],
        ["OS-3", "Create the SRS user for this environment and map it to the index-scoped role `pega26-<code>-srs` (Section 7.5).", "Search engineer", "User can create and delete `pega26-<code>-test`; cannot touch another prefix", "Test output"],
        ["OS-4", "Store the SRS user credentials in `kv-pega-<code>`.", "Search engineer", "Secret synced to `srs-<code>`", "kubectl output"],
    ])
    b.h2("SRS")
    _steps_table(b, "SRS steps", [
        ["SR-1", "Create the SRS TLS keystore and truststore and store them in Key Vault.", "Platform team", "Secret `srs-runtime-certs` synced", "kubectl output"],
        ["SR-2", "Deploy SRS: `helm upgrade --install srs-<code> pega/backingservices -n srs-<code> -f backingservices-<code>.yaml`.", "Search engineer", "SRS pods Ready (P-1)", "Output"],
        ["SR-3", "From a pod in `pega-<code>`, call the SRS service with and without a token.", "Search engineer", "Without token refused; with token accepted (S-5)", "Output"],
    ])
    b.h2("Database clone and upgrade")
    _steps_table(b, "Database clone and upgrade steps", [
        ["DB-1", "For non-production, take the clone from the agreed production copy; for PROD, take the final clone at cutover step C-3.", "DBA team", "Clone restored; row counts recorded", "Clone record"],
        ["DB-2", "Mask the clone (non-production) per OD-07.", "DBA team", "Masking report", "Report"],
        ["DB-3", "Apply any pre-upgrade condition from Pega Support (GQ-02, GQ-03) and the time-point B items in {ref:tab_inventory}.", "DBA team, Pega LSA", "Each item signed off", "Clean-up record"],
        ["DB-4", "Run U: `helm upgrade --install pega pega/pega -n pega-<code> -f pega-<code>-upgrade.yaml --version 4.13.0`.", "Platform team", "Installer job completed (P-5)", "Installer log, duration"],
        ["DB-5", "If the installer job fails, read the log, fix the cause, and follow Pega's guidance for rerunning the upgrade on this database. If in doubt, restore the clone and start again from DB-1 (FS-26).", "Platform team, DBA", "Rerun completes", "Incident record"],
    ])
    b.h2("First start, index build and intake release")
    b.p("Follow the first-start control in Section 10.4 (steps ST-1 to ST-9). The Helm commands are:")
    b.code("""# Run F: web tier only, batch tier held at zero
helm upgrade --install pega pega/pega -n pega-<code> -f pega-<code>-first.yaml \\
  --version 4.13.0
# Run D: steady state, batch tier at normal size (starts queue processing)
helm upgrade --install pega pega/pega -n pega-<code> -f pega-<code>-deploy.yaml \\
  --version 4.13.0""", title="Helm commands for runs F and D")
    b.h2("Per-environment notes")
    b.table(["Environment", "Built from", "Masked", "Shared group", "Notes"], [
        ["DEV", "Production copy", "Yes", "NP1", "First build. Proves the Okta claim design, the index-scoped role, DSS precedence and the full path; finds the cluster messaging topics."],
        ["SIT", "Production copy (can be the DEV clone)", "Yes", "NP1", "First environment with integrations to test systems; data set register applied."],
        ["UAT", "Recent production copy", "Yes", "NP1", "Business tests on search over masked data."],
        ["PERF", "Full-size production copy", "Yes", "NP2", "Load tests, partition and index build measurements; sets PROD sizes."],
        ["PREPROD", "Most recent full-size production copy", "Per policy", "NP2", "Rehearsal 1 and Rehearsal 2 of the production cutover, run by the cutover team."],
        ["PROD", "Final clone at cutover", "No", "PRD", "Section 13."],
    ], caption="Per-environment notes", widths=[2.2, 3.6, 1.6, 2, 7.2], size=8.5)


def s13_cutover(b):
    b.h1("Production cutover and rollback")
    b.h2("Principles")
    b.bullets([
        "The 8.8 system and its database are not changed by the cutover, apart from stopping 8.8. They stay available for rollback until the rollback window closes.",
        "Every step was run at least twice in PREPROD with production-sized data, by the people who will run it in production.",
        "The outage window comes from the rehearsal measurements plus 25 % contingency, not from estimates.",
        "Rollback is free of data loss until intake is released on 26.1.1. After that, rollback loses work done on 26.1.1, so the business decides.",
    ])
    b.h2("Milestones")
    b.table(["Milestone", "Content", "Exit criteria"], [
        ["M1 Design approval", "This document approved; open decisions owned", "Signatures on the approvals page"],
        ["M2 DEV build", "First environment from a clone", "First-start Go/No-Go passed; Okta, role and DSS tests recorded"],
        ["M3 PERF measurements", "Load tests, partitions, index build time", "PROD sizes and cluster type agreed (OD-02)"],
        ["M4 Rehearsal 1 (PREPROD)", "Full cutover sequence with timings", "All steps completed; defects logged"],
        ["M5 Rehearsal 2 (PREPROD)", "Full cutover sequence by the cutover team", "Timing fits the window; no open severity 1 or 2 defects"],
        ["M6 Go/No-Go 1 and production cutover", "Section 13.3", "Go/No-Go 3 passed"],
    ], caption="Programme milestones used in this document", widths=[4, 6, 6.6], size=9)
    b.h2("Cutover sequence")
    b.figure(GEN + "fig_cutover_timeline.png", "Production cutover sequence from the Kafka and search point of view", OWN, width_cm=16.5)
    b.table(["Step", "Action", "Owner", "Duration from", "Evidence"], [
        ["C-1", "Hold intake on 8.8: block user access, stop inbound listeners and services, disable job schedulers that create work.", "Application team", "Rehearsal", "Change record"],
        ["C-2", "Let queue processors finish. Record the count of items ready to process (must be zero) and the count of broken items per queue processor from Admin Studio. Record the last committed offset of each application Kafka data set consumer.", "Pega LSA", "Rehearsal", "Screenshots, offset list"],
        ["C-3", "Stop 8.8. Take the final clone (DB-1).", "DBA team", "Rehearsal", "Clone record"],
        ["C-4", "Run U on the clone (DB-3, DB-4).", "Platform team", "Rehearsal", "Installer log"],
        ["C-5", "Apply time-point A clean-up; run F; time-point F checks (ST-2 to ST-6).", "Pega LSA", "Rehearsal", "Clean-up record, screenshots"],
        ["C-6", "Go/No-Go at first start ({ref:fig_gonogo}).", "Cutover manager", "Fixed", "Gate record"],
        ["C-7", "Run D; full index build; completeness and count checks (ST-7, ST-8).", "Pega LSA", "Rehearsal", "Count sheet"],
        ["C-8", "Application Kafka data sets cutover (Section 13.5).", "Application team", "Rehearsal", "Offset evidence"],
        ["C-9", "Smoke tests; Go/No-Go 2.", "Test lead", "Rehearsal", "Test report, gate record"],
        ["C-10", "Switch public DNS to Application Gateway; release intake (ST-9); Go/No-Go 3 after 30 minutes.", "Platform team", "DNS TTL", "DNS change record"],
    ], caption="Production cutover steps", widths=[1.1, 8.4, 2.5, 2, 2.6], size=8.5)
    b.callout("important", "Lower the TTL of the public DNS record to 300 seconds at least 48 hours before cutover, so a DNS switch "
              "or revert takes effect quickly. Restore the normal TTL after hypercare.")
    b.h2("Go/No-Go gates")
    b.table(["Gate", "When", "Criteria", "Decision owner"], [
        ["Go/No-Go 1", "Seven days before", "Two PREPROD rehearsals passed; window fits with 25 % contingency; Pega Support answers received or conservative plan accepted; rollback rehearsed", "Business owner with platform lead"],
        ["First-start gate", "After C-5", "All checks in {ref:fig_gonogo} up to the index build", "Cutover manager"],
        ["Go/No-Go 2", "After C-9", "Index build complete and counts match; application data sets started at agreed offsets; smoke tests pass", "Cutover manager"],
        ["Go/No-Go 3", "30 minutes after C-10", "No severity 1 or 2 incidents; queue backlog falling; search response within target", "Cutover manager with business owner"],
    ], caption="Go/No-Go gates", widths=[2.6, 3, 8.2, 2.8], size=9)
    b.h2("Application Kafka data set cutover")
    b.steps([
        "At C-2, record the last committed offset of each 8.8 consumer group that reads the customer's Kafka topics (K-8 on the customer's cluster).",
        "For data sets that keep the same cluster and topic, configure the 26.1.1 data flow to start from the recorded offset, or reuse the same consumer group if the application team confirms it, so no message is skipped or processed twice.",
        "For data sets that move to a new cluster without history, start from new records only, and keep the 8.8 offset list as evidence of what was processed.",
        "For data sets mirrored with Cluster Linking, promote the mirror topics at cutover; Cluster Linking keeps offsets [R35].",
        "Record the first offset processed by 26.1.1 for each data set and compare with step 1.",
    ])
    b.h2("Rollback")
    b.table(["Step", "Action"], [
        ["RB-1", "Declare rollback; record the reason and the time."],
        ["RB-2", "Hold intake on 26.1.1. If intake was released, export the list of cases created or changed on 26.1.1 for reconciliation."],
        ["RB-3", "Revert public DNS to 8.8."],
        ["RB-4", "Start 8.8 on its untouched database. Its embedded Kafka and embedded Elasticsearch were stopped, not changed."],
        ["RB-5", "Check the 8.8 stream and search landing pages and queue processors; release 8.8 intake."],
        ["RB-6", "Reset application Kafka data set consumers on 8.8 to the offsets agreed for the rollback."],
        ["RB-7", "Scale 26.1.1 to zero; keep it and its Kafka topics and indexes for analysis."],
    ], caption="Rollback steps", widths=[1.4, 15.2], size=9)
    b.p("The point after which rollback loses work is C-10, when intake is released on 26.1.1. Before C-10, rollback loses "
        "nothing. After C-10, cases created or changed on 26.1.1 are not in the 8.8 database, and messages produced to "
        "application Kafka topics by 26.1.1 have been consumed downstream. The business owner decides at that point between "
        "rollback with reconciliation and fixing forward, using the reconciliation list from RB-2.")


def s14_testing(b):
    b.h1("Test strategy, rehearsals and failure scenarios")
    b.h2("Test stages")
    b.table(["Stage", "Entry criteria", "Environment", "Owner", "Evidence"], [
        ["Connectivity", "Network, DNS and secrets steps done", "Every environment", "Platform team", "K-1 to K-3, S-1 to S-3, O-1 outputs"],
        ["Configuration", "Run F complete", "Every environment", "Pega LSA", "Landing page screenshots; inventory sign-off"],
        ["Functional", "Run D and index build complete", "DEV, SIT, UAT", "Test lead", "Checks in Section 14.4"],
        ["Isolation", "Two environments in a group running", "NP1, NP2", "Security architect", "IT-01 to IT-10 records"],
        ["Performance", "PERF built at full size", "PERF", "Performance lead", "PT-01 to PT-04 reports"],
        ["Resilience and failure", "Performance baseline recorded", "PERF, PREPROD", "Platform team", "Failure catalogue records (Section 14.6)"],
        ["Security", "Isolation tests passed", "SIT, PREPROD", "Security architect", "No public endpoints; secret scan of values; token claim checks; TLS versions"],
        ["Operational acceptance", "Monitoring live", "PREPROD", "Operations lead", "Alerts reach on-call; runbooks used by operations staff"],
        ["Full rehearsal", "All above passed", "PREPROD (twice)", "Cutover manager", "Timed cutover record (Appendix D)"],
    ], caption="Test stages", widths=[2.8, 4, 2.6, 2.8, 4.4], size=8.5)
    b.h2("Rehearsals and measurements")
    b.p("Rehearse the full clone-and-upgrade path at least twice in PREPROD on production-sized data before production. "
        "Record each measurement against data volume, because they set the production window.")
    b.table(["Measurement", "Steps", "Used for", "Rehearsal 1", "Rehearsal 2"], [
        ["Drain time on 8.8", "C-1 to C-2", "Window", "", ""],
        ["Clone time", "C-3", "Window", "", ""],
        ["Upgrade time", "C-4", "Window", "", ""],
        ["Clean-up time", "C-5", "Window", "", ""],
        ["First start time", "ST-3 to ST-6", "Window", "", ""],
        ["Full index build time", "ST-7 to ST-8", "Window; OpenSearch sizing", "", ""],
        ["Time to release intake", "C-9 to C-10", "Window", "", ""],
        ["Partitions created", "K-5", "Confluent capacity", "", ""],
        ["Searchable data volume", "S-4", "OpenSearch sizing", "", ""],
    ], caption="Rehearsal measurements", widths=[4, 3, 4, 2.8, 2.8], size=9)
    b.h2("Isolation tests")
    b.p("Each test uses environment A's credentials against environment B in the same group, and must be refused. Run them "
        "in NP1 and NP2 after every new environment joins a group.")
    b.table(["ID", "Test", "Method", "Pass criteria"], [
        ["IT-01", "Read and write B's topics with A's key", "kcat produce and consume to `pega-<B>-<topic>` with A's credentials", "Authorization error"],
        ["IT-02", "Create and delete topics under B's prefix", "`confluent kafka topic create` and `delete` as A", "Refused"],
        ["IT-03", "Join or reset B's consumer group", "kcat consumer with group `pega-<B>-...`", "Authorization error"],
        ["IT-04", "Use A's key from B's namespace", "Check B's Key Vault and secrets contain no A key", "Not present"],
        ["IT-05", "Index names after the build", "S-4 for `pega26-<A>*`; list all indexes", "A's indexes all carry A's prefix; none outside a known prefix"],
        ["IT-06", "A's SRS user on B's indexes; SRS works with the scoped role", "Search, write and delete on `pega26-<B>*` as A's user; full build as A", "Refused on B; A's build succeeds"],
        ["IT-07", "A's token at B's SRS", "Send a request to B's SRS with A's token", "Refused (guid mismatch)"],
        ["IT-08", "A's External Secrets identity on B's vault", "Create a test ExternalSecret in A pointing at B's vault", "Access denied"],
        ["IT-09", "Non-production pod to production endpoints", "From a pod in NP1 and NP2: DNS and TCP to cc-prd, os-prd and production integration hosts", "No private resolution; connection refused by firewall"],
        ["IT-10", "Cloned environment to production integrations", "Firewall log review during run F and the first day of run D", "No connection attempts to production systems"],
    ], caption="Isolation tests", widths=[1.3, 4.2, 6.4, 4.7], size=8.5)
    b.h2("Functional and integration checks")
    b.bullets([
        "Queue a test item to a test queue processor and confirm it is processed; repeat after every deployment.",
        "Run a job scheduler with a test activity and confirm it runs on the batch tier.",
        "Create a case, wait for indexing, and find it with case search; repeat for each class with custom search properties (CD-14).",
        "Run each report that depends on search and compare with the 8.8 baseline on the same clone data.",
        "For each application Kafka data set in SIT, run its data flow against the test topic and compare counts.",
        "Check the produce path with a message near 5,000,000 bytes, if the application produces large messages (FS-06).",
    ])
    b.h2("Performance tests")
    b.table(["ID", "Test", "Target", "Measured"], [
        ["PT-01", "Peak user load plus peak queue processor load in PERF", "Agreed response times; consumer lag returns to baseline after peak", ""],
        ["PT-02", "Full index build throughput", "Fits the production window after scaling (Section 7.8)", ""],
        ["PT-03", "Quota enforcement: PERF load while PREPROD runs a light test", "PREPROD response unchanged; PERF throttled at its quota", ""],
        ["PT-04", "Consumer lag under peak per queue processor", "Lag within the alert threshold", ""],
    ], caption="Performance tests", widths=[1.3, 6.6, 6, 2.7], size=9)
    b.h2("Failure scenario catalogue")
    b.p("{ref:tab_fail} lists the failures to test. Run Kafka, search and platform scenarios in PERF or PREPROD, and "
        "clone-specific scenarios in DEV during the first build and again in PREPROD. Where Pega does not document the exact "
        "behaviour, record what happens in the first run; that record becomes the expected result for later runs.")
    rows = [
        ["FS-01", "Kafka bootstrap unreachable", "Block 9092 to the Confluent endpoints with a network policy", "Queue processing and cluster messaging stop; Stream landing page not NORMAL", "Stream landing page; Pega log Kafka connection errors; alert", "Remove the block; pods reconnect or restart", "Processing resumes; no item lost"],
        ["FS-02", "Zonal private DNS record missing", "Remove one zonal record in DEV", "Some broker connections fail after bootstrap", "K-3 shows a broker resolving publicly or not at all", "Restore the record", "All broker names resolve privately"],
        ["FS-03", "API key revoked", "Delete the environment's API key in DEV", "Authentication failures; stream down", "Pega log SASL errors; Confluent audit log", "Create a key; update Key Vault; restart tiers", "Stream NORMAL within the rotation time"],
        ["FS-04", "ACL missing for a new topic", "Remove the TOPIC prefixed ACL briefly in DEV", "Topic creation or access refused", "Authorization errors in Pega log", "Restore the ACL; add literal ACLs for unprefixed topics", "All topics accessible"],
        ["FS-05", "Partition limit reached", "Lower the cluster headroom in a sandbox or simulate with a test topic set", "New topic creation fails", "Confluent error; Pega log", "Delete unused topics or add capacity", "New queue processor starts"],
        ["FS-06", "Message larger than max.message.bytes", "Produce a 6 MB test message through a test queue processor", "Producer error for that item", "RecordTooLargeException in Pega log", "Set topic to 5,000,000; keep messages within it [R11]", "Item within limit processed"],
        ["FS-07", "Broker rolling restart during Confluent maintenance", "Observe a scheduled maintenance in PERF", "Short retries; no loss", "Confluent notice; brief lag rise", "None", "No broken items caused"],
        ["FS-08", "Consumer lag builds under load", "PT-04 at 150 % of peak", "Lag grows then drains", "Lag alert", "Add batch pods within partition count", "Lag back to baseline"],
        ["FS-09", "One SRS pod lost", "Delete one SRS pod in PERF", "Searches continue on other pods", "Pod restart event", "Kubernetes recreates it", "No search errors seen by users"],
        ["FS-10", "Whole SRS deployment lost", "Scale SRS to zero in PERF", "Search and indexing fail; other functions continue", "Search errors; SRS alert", "Scale back; check indexing backlog clears", "Backlog cleared; counts match"],
        ["FS-11", "Okta token cannot be obtained", "Block `<okta-domain>` at the firewall for the environment", "Search fails once the current token expires", "Pega log token errors", "Restore the rule", "Search resumes without restart, or with restart recorded"],
        ["FS-12", "Token from the wrong issuer", "Configure a test client on another authorization server", "SRS refuses if it checks issuer; record result", "SRS log", "Use the right server", "Behaviour recorded in Section 18.4"],
        ["FS-13", "`guid` does not match customerDeploymentId", "Change the claim value for the DEV client", "SRS refuses requests", "401 or 403 in SRS log", "Restore the claim", "Search resumes"],
        ["FS-14", "Client key rotated in Okta but not in Key Vault", "Remove the current public key from the DEV client", "Token requests fail", "Okta system log; Pega log", "Register the key or update Key Vault and restart", "Search resumes"],
        ["FS-15", "OpenSearch status yellow", "Stop one data node (provider tooling) in PERF", "Searches continue", "S-2 yellow; alert", "Provider restores the node", "Green; no Pega errors"],
        ["FS-16", "OpenSearch status red", "Simulate in a sandbox service by closing an index copy", "Searches on the affected index fail", "S-2 red; alert", "Restore or rebuild the index", "Green; counts match"],
        ["FS-17", "Flood-stage disk watermark", "Fill test data on a sandbox service", "Indexes read-only; indexing fails", "Disk alert; SRS errors", "Add storage; clear the read-only block as the provider documents", "Indexing resumes"],
        ["FS-18", "OpenSearch credentials rotated without SRS update", "Change the SRS user password only", "SRS calls refused", "SRS log 401", "Update Key Vault; restart SRS", "Search resumes"],
        ["FS-19", "Certificate expires", "Deploy an expired SRS server certificate in DEV", "Pega to SRS TLS fails", "TLS errors in Pega log; expiry alert should have fired earlier", "Renew; restart", "Expiry alert fires 30 days before"],
        ["FS-20", "Key Vault secret rotated without pod restart", "Rotate the API key, delete the old key, skip the restart", "Stream fails when the old key is deleted", "SASL errors", "Rolling restart", "Runbook includes the restart"],
        ["FS-21", "AKS node drained or zone lost", "Cordon and drain all nodes in one zone", "Pods reschedule within PDB limits", "Pod events", "Kubernetes reschedules", "Processing and search continue"],
        ["FS-22", "Non-production load test saturates the shared cluster", "PERF load above its quota while PREPROD tests", "PERF throttled; PREPROD unaffected", "Metrics API by principal", "Lower quota; reschedule", "PREPROD response unchanged"],
        ["FS-23", "Index rebuild during business hours on a shared service", "Full build in SIT while UAT tests search", "UAT search slower", "Latency metrics", "Schedule builds out of hours", "UAT latency within target"],
        ["FS-24", "Stale 8.8 stream or search DSS overrides Helm", "In DEV, record cloned DSS; start with them in place", "Landing pages show Helm values (expected) or DSS values (defect)", "Stream and search landing pages", "Follow Pega Support's answer to GQ-05", "Helm values in effect"],
        ["FS-25", "Wrong customerDeploymentId deployed", "Deploy SIT with DEV's ID in a sandbox", "SRS refuses tokens; if accepted, indexes mix", "Pipeline check should block it; SRS log", "Redeploy with the right ID; delete wrong indexes", "Pipeline check blocks the deploy"],
        ["FS-26", "Installer upgrade fails halfway", "Stop the installer job during a DEV rehearsal", "Database left partly upgraded", "Job status; installer log", "Follow Pega's rerun guidance, or restore the clone and restart", "Second run completes"],
        ["FS-27", "Clone starts with application Kafka data sets pointing to production", "Leave one data set unchanged in DEV, with the firewall rule in place", "Connection denied by the firewall", "Firewall log; data set errors", "Repoint or disable the data set", "No production connection; IT-10 passes"],
        ["FS-28", "Delayed or broken items from 8.8 processed unexpectedly", "Keep a sample of items in a DEV clone", "Items run on 26.1.1 when due or requeued", "Queue processor statistics; application log", "Apply the decision per queue processor (CD-05, CD-06)", "Behaviour matches the decision"],
        ["FS-29", "Index build interrupted", "Restart the batch tier during the build in DEV", "Build stops or continues", "Search landing page", "Resume or restart the build as Pega documents [R17]", "Complete build; counts match"],
        ["FS-30", "All batch pods lost", "Scale the batch tier to zero in PERF under load", "Queue processing stops; items accumulate in topics", "Queue backlog alert", "Scale back", "Backlog drains; no loss"],
    ]
    b.table(["ID", "Scenario", "How to cause it safely", "Expected behaviour", "Detection", "Recovery", "Pass criteria"], rows,
            caption="Failure scenario catalogue", widths=[1.1, 2.4, 2.9, 2.6, 2.6, 2.6, 2.4], size=7, label="fail")
    b.h2("Exact checks")
    b.table(["Check", "Command or screen", "Expected result"], [
        ["Stream service", "Dev Studio: Configure > Decisioning > Infrastructure > Services > Stream", "Provider ExternalKafka; status NORMAL; bootstrap and prefix from Helm [R13]"],
        ["Queue processors", "Admin Studio > Queue processors", "Ready to process falls to zero; broken items known"],
        ["Search", "Search landing page", "SRS connected; all classes indexed; no CONFLICTS FOUND [R19]"],
        ["Kafka DNS, TLS and metadata", "K-1, K-2, K-3", "Private IPs; trusted chain; all brokers listed"],
        ["Topics, partitions, configuration, ACLs", "K-4 to K-7", "Topics under `pega-<code>-` only; max.message.bytes 5,000,000; ACLs as {ref:tab_acls}"],
        ["OpenSearch health, settings, indexes", "S-2, S-3, S-4", "Green; both settings; indexes under `pega26-<code>` only"],
        ["SRS", "S-5", "Token required; healthy response"],
        ["Okta token", "O-1, O-2", "`scp` includes `pega.search:full`; `guid` equals `pega26-<code>`"],
        ["Installer job", "P-5", "Completed without errors"],
        ["Pods and secrets", "P-1, P-4", "All Ready; all ExternalSecrets SecretSynced"],
    ], caption="Exact checks", widths=[3.6, 6.4, 6.6], size=8.5)
    b.h2("Acceptance criteria")
    b.table(["ID", "Criterion"], [
        ["AC-1", "All exact checks pass in every environment, with evidence filed."],
        ["AC-2", "All isolation tests pass in NP1 and NP2."],
        ["AC-3", "All failure scenarios have been run at least once with results recorded; any defect is fixed or accepted by the business owner."],
        ["AC-4", "Performance results meet the targets agreed by the business owner."],
        ["AC-5", "Two PREPROD rehearsals completed, with the measured window within the agreed outage."],
        ["AC-6", "Monitoring and alerts in Section 17.1 are live and tested."],
    ], caption="Acceptance criteria", widths=[1.4, 15.2], size=9)
