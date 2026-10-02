"""Section 16 (performance engineering and sizing) and Section 19 (observability, monitoring and logging)."""
from content_a import GEN, OWN
import sizing_calc as SC


def s15_perf(b):
    b.h1("Performance engineering and sizing")
    b.h2("Why performance testing is required")
    b.p("Load figures from Pega 8.8 cannot be carried over to 26.1.1 on AKS. Too much changes at once, and each change "
        "moves load to a service that 8.8 never used:")
    b.bullets([
        "Every queue item, cluster message and index update now crosses the network to Confluent Cloud or to SRS and OpenSearch, through private endpoints. On 8.8 these stayed inside the Pega nodes.",
        "Queue processing in '26 is partitioned and multi-threaded [R3], so throughput depends on partitions, threads and batch pods together (Section 6.7).",
        "From '25, cluster messaging that Hazelcast carried uses Kafka [R7]. Kafka load rises with the number of Pega pods, not only with business volume.",
        "Confluent enforces connection and request limits on Enterprise clusters [R31]. A design that works at average load can be throttled at peak or during a rolling restart.",
        "Non-production environments share clusters and search services. Contention between them only shows up under load.",
        "The full index build sets part of the production outage [R15], and its time depends on resources that only a full-size test can show.",
        "Pega asks clients to start from its default search sizing and adjust it after measuring [R14].",
    ])
    b.p("Performance testing is therefore a gate, not a formality. PROD sizes are signed off only from PERF results (milestone "
        "M3), and PREPROD rehearsals confirm them.")

    b.h2("Workload model")
    b.p("The workload model describes production load in terms the tests can reproduce. Build it from 8.8 production data "
        "(AS-10), not from estimates, and get the business owner to approve it before the first test.")
    b.table(["Input", "Source on 8.8", "Used for"], [
        ["Peak concurrent users and sessions per hour, by user journey", "Web server or gateway logs; Pega Diagnostic Center; Pega usage reports", "Web tier load scripts"],
        ["API calls per hour by service", "Gateway logs; Pega service rule statistics", "API load scripts"],
        ["Cases created and resolved per hour, by case type", "Pega reports on the work tables", "Data growth; indexing rate"],
        ["Queue items per hour per queue processor, and the busiest queue processors", "Admin Studio queue processor statistics", "Kafka produce and consume rates; partitions"],
        ["Job scheduler runs and their duration", "Admin Studio", "Batch tier load windows"],
        ["Search queries and search-based reports per hour", "Pega logs; report statistics", "SRS and OpenSearch query rate"],
        ["Calendar peaks: month end, campaigns, seasonal", "Business owner", "Peak-hour definition"],
        ["Data volume and yearly growth", "Database sizes; DEV index sizes (S-4)", "Storage sizing"],
    ], caption="Workload model inputs", widths=[5.6, 6, 5], size=8.5)
    b.p("Define one design peak hour that combines the busiest user load with the busiest background load seen together on "
        "8.8, plus the agreed growth. All targets in this section refer to that hour.")

    b.h2("Test types and measurement points")
    b.table(["Test", "Purpose", "Profile", "Pass criteria"], [
        ["Baseline", "Reference figures with fixed replica counts", "20 % of design peak, HPA off, 1 hour", "Recorded; used to compare every later run"],
        ["Load", "Prove the design peak hour", "Ramp to 100 % over 30 minutes; hold 1 hour", "Response times and lag within targets; no throttling"],
        ["Stress", "Find the first limit and how the system fails", "Step up by 25 % each 20 minutes until a target fails", "Breaking point at least 150 % of peak; the first limit is known"],
        ["Soak", "Find leaks and slow drift", "80 % of peak for at least 8 hours, across a token expiry and a key rotation if planned", "No heap growth trend; stable lag; no rising error rate"],
        ["Spike", "Prove HPA and Kafka absorb a sudden rise", "From 30 % to 120 % within 2 minutes", "Recovery to target within 10 minutes"],
        ["Backlog drain", "Prove the batch tier clears a backlog", "Queue one peak hour of items with the batch tier at zero, then start it", "Drained within the agreed time; no broken items"],
        ["Index build", "Measure the outage component", "Full build on the full-size clone (PT-02)", "Fits the window after scaling (Section 7.8)"],
        ["Resilience under load", "Prove zone and component loss at peak", "FS-09, FS-15, FS-21 and FS-31 run during a load test", "Targets met within the recovery time"],
        ["Noisy neighbour", "Prove quotas protect the shared group", "PT-03", "PREPROD response unchanged"],
    ], caption="Performance test types", widths=[2.6, 3.8, 5, 5.2], size=8.5, label="perf_types")
    b.p("{ref:fig_harness} shows the test set-up and the six measurement points. Every test records all six, so a slow "
        "response at M1 can be traced to the layer that caused it.")
    b.figure(GEN + "fig_perf_harness.png", "Performance test harness and measurement points in PERF", OWN, width_cm=13, label="harness")
    b.table(["Point", "What is measured", "Source"], [
        ["M1", "Response time (median, 95th and 99th percentile) and errors per journey", "Load tool"],
        ["M2", "Pod CPU, memory, heap after GC, GC pause time, HPA events, pod restarts", "Managed Prometheus; GC log (Section 10.2)"],
        ["M3", "Bytes in and out, requests, connections, consumer lag and throttling per service account", "Confluent Metrics API [R56]"],
        ["M4", "Ready to process, throughput and broken items per queue processor", "Admin Studio"],
        ["M5", "SRS response time and errors; OpenSearch query latency, indexing rate, rejected requests", "SRS logs; provider metrics"],
        ["M6", "Database CPU, waits, connections and slow statements", "Database monitoring"],
    ], caption="Measurement points", widths=[1.3, 9.3, 6], size=8.5)

    b.h2("Tools and harness")
    b.bullets([
        "Use the customer's standard load tool, for example Apache JMeter or Gatling. Run the generators on their own VMs or node pool in a separate subnet, never on the Pega node pools, and enter through Application Gateway so the path matches production.",
        "Record scripts against 26.1.1, not 8.8. Pega UI requests carry session-specific values that must be correlated in the script; a script recorded on 8.8 will fail or produce false errors.",
        "Drive Kafka and search through Pega. Direct load on Confluent or OpenSearch does not show how Pega uses them. A short `kafka-producer-perf-test` run from a Pega namespace pod is useful only as a baseline for the Private Link path.",
        "Use the full-size masked clone. Take a database snapshot before the first test and restore it between test cycles, then refresh topics and indexes as in Section 20.3, so each cycle starts from the same state.",
        "Synchronize all clocks to UTC and label each run with a run ID in the load tool, in Grafana annotations and in the test log, so measurements from every source can be lined up.",
        "Agree each test with the identity team. All environments share one Okta org, and load tests add token requests to the org's rate limit [R52].",
    ])

    b.h2("Entry and exit criteria")
    b.table(["Criteria", "Detail"], [
        ["Entry", ["PERF built at full size with the PROD cluster type and OpenSearch size; full index build complete.",
                   "Workload model and targets approved by the business owner.",
                   "Dashboards for M1 to M6 live (Section 19.4); synthetic checks green.",
                   "PREPROD activity scheduled away from the test window (Section 5.4)."]],
        ["Exit", ["Load, soak and spike tests pass at the design peak; stress test shows at least 150 % headroom.",
                  "No Confluent throttling at peak; consumer lag returns to baseline within the agreed time.",
                  "Index build time fits the window with the PROD sizes.",
                  "Sizing calculator updated with measured values; PROD sizes and cluster type signed off (M3)."]],
        ["Suspend", ["A shared-service incident, another environment's activity, or a defect that invalidates results. Record and rerun."]],
    ], caption="Performance test entry, exit and suspension criteria", widths=[2.4, 14.2], size=9)

    b.h2("Pitfalls seen in Pega performance tests")
    b.bullets([
        "**Empty or partial search indexes.** Queries on a small index are fast and say nothing about production. Test only after the full build.",
        "**HPA hiding the limit.** Run the baseline and the stress test with fixed replicas, then repeat the load test with HPA on.",
        "**Warm-up included in results.** Exclude the first 15 minutes after a start, while caches fill and the JIT compiles.",
        "**Fewer partitions than production.** If PERF topics have fewer partitions than PROD will, batch results are pessimistic; if more, they are optimistic. Keep the partition DSS the same in PERF and PROD (CD-15).",
        "**Web-only scripts.** User journeys that create cases also create queue items and index updates. Measure M4 and M5 in every run, not only M1.",
        "**Repeated search terms.** OpenSearch caches results. Use a large, varied set of search values from the masked data.",
        "**Comparing with 8.8 figures measured differently.** Compare like with like, or use 8.8 figures only as a guide.",
        "**Connections not measured.** Record connections and connection attempts per pod (M3) at rest, at peak and during a restart, because Confluent limits them per cluster [R31].",
    ])

    b.h2("Sizing method")
    b.p("Sizing runs as a loop, shown in {ref:fig_sizing}. Production facts from 8.8 and measurements from DEV go into the "
        "sizing calculator (Appendix H). PERF tests the result at production volume. If targets are not met with headroom, "
        "the inputs or sizes are adjusted and PERF runs again. After go-live, production monitoring feeds actual usage back "
        "into the calculator at each quarterly capacity review.")
    b.figure(GEN + "fig_sizing_flow.png", "Sizing loop from production facts to signed-off PROD sizes", OWN, width_cm=16.5, label="sizing")

    b.h2("Sizing rules per layer")
    b.table(["Layer", "Rule", "Source"], [
        ["Pega web tier", "Pods at peak = peak sessions / sessions per pod measured in PERF at target response time. HPA maximum = pods at peak x 1.25", "Measured; [R23]"],
        ["Pega batch tier", "Effective consumers per queue processor = min(partitions, batch pods x threads). Size pods for the busiest queue processors and for the index build, whichever needs more", "[R49, R50]"],
        ["Pega pod memory", "Container 12Gi with heap about two thirds of it; metaspace capped at 768m", "[R23, R63]"],
        ["Confluent capacity units", "Units = the largest of: ingress / 60 MBps, egress / 180 MBps, partitions / 3,000 (4,500 on Dedicated), connections / 18,000, requests per second / 7,500 (15,000), and 2 for the SLA", "[R31]"],
        ["Confluent partitions", "Topics x partitions per topic (default 6), plus 30 % headroom, summed over the group", "[R49]"],
        ["OpenSearch storage and nodes", "Formulas in {ref:tab_os_formulas}", "[R54, R55]"],
        ["SRS", "3 pods in PERF, PREPROD and PROD; add pods if SRS CPU stays above 70 % at peak", "[R14, R24]"],
        ["Okta", "Token requests per minute summed over all environments, compared with the org's token endpoint limit", "[R52]"],
        ["AKS nodes", "Pega pods per node = the smaller of allocatable CPU / CPU request and allocatable memory / memory request. Nodes = (pods at HPA maximum / pods per node) x 1.5 for zone loss, plus 1 for upgrade surge, rounded up to a multiple of 3", "[R59]"],
    ], caption="Sizing rules per layer", widths=[3.2, 11, 2.4], size=8.5, label="sizing_rules")

    b.h2("Worked example")
    ex = SC.example()
    b.callout("caution", "The figures below are illustrative inputs chosen to show the method. They are not measurements "
              "of the customer's system. Replace every input with a measured value before sizing anything.")
    k, o, a = ex["kafka"], ex["opensearch"], ex["aks"]
    b.table(["Layer", "Inputs (illustrative)", "Result"], [
        ["Confluent cc-prd", f"{k['ingress']} MBps in, {k['egress']} MBps out, {k['partitions']} partitions measured, {k['connections']:,} connections, {k['requests']:,} requests per second",
         f"Units needed by {', '.join(f'{n} {v}' for n, v in k['by_limit'].items())}. Result: {k['units']} eCKU, set by the {k['driver']}"],
        ["OpenSearch os-prd", f"{o['primary_gib']} GiB primary data, {o['replicas']} replica, {int(o['growth'] * 100)} % growth a year for {o['years']} years, {o['indexes']} indexes with {o['primaries']} primary shard each, {o['disk_gib']} GiB usable disk and {o['heap_gib']} GiB heap per node",
         f"Storage {o['storage_gib']} GiB; nodes by storage {o['nodes_storage']}, by shards {o['nodes_shards']}, zone minimum 3. Result: {o['nodes']} data nodes"],
        ["AKS Pega node pool", f"{a['pods']} Pega pods at HPA maximum, {a['cpu_req']} CPU and {a['mem_req']} GiB each; nodes with {a['alloc_cpu']} CPU and {a['alloc_mem']} GiB allocatable",
         f"{a['per_node']} pods per node; {a['base']} nodes for the load; x 1.5 and + 1 gives {a['nodes']} nodes"],
    ], caption="Worked sizing example (illustrative inputs)", widths=[3, 7.6, 6], size=8.5)
    b.p("In this example the Confluent cluster is sized by the SLA minimum, not by load, and the OpenSearch service by the "
        "three-zone minimum. That is common for Pega workloads of this kind. The shared clusters change the picture: in NP1, "
        "three environments' partitions add up, and partitions or connections can set the unit count instead. Run the "
        "calculator for each group, not only for PROD.")


def app_h_calculator(b):
    b.h1("Sizing calculator", appendix="H")
    b.p("The sizing calculator is the Excel workbook `Pega_26_Sizing_Calculator.xlsx`, issued with this document. It "
        "applies the rules in {ref:tab_sizing_rules} and {ref:tab_os_formulas} with live formulas. Yellow cells are inputs and "
        "green cells are formulas. The example inputs are illustrative, as in Section 16.9, and must be replaced with "
        "measured values.")
    b.table(["Sheet", "Inputs", "Outputs", "Sources of constants"], [
        ["Kafka", "Per group: cluster type, peak ingress and egress, measured partitions, headroom, connections, requests per second", "Units needed by each limit; capacity units; the limit that sets them; warnings above 10 and 32 eCKU", "[R31, R49]"],
        ["OpenSearch", "Per service: primary data, replicas, growth, years, rebuild peak, indexes, shards per index, disk and heap per node", "Storage; total shards; data nodes by storage, by shards and by zones; average shard size", "[R54, R55]"],
        ["AKS", "Pega pods at HPA maximum, pod requests, node allocatable CPU and memory", "Pods per node; nodes for the load; nodes with zone headroom and surge", "[R23, R59]"],
        ["Okta", "Pods and measured token requests per pod per hour, per environment; org token endpoint limit", "Token requests per minute; share of the org limit", "[R52]"],
    ], caption="Sizing calculator sheets", widths=[2.2, 6, 5.6, 2.8], size=8.5)
    b.h2("Example outputs")
    rows = []
    for g, v in SC.KAFKA_EXAMPLE.items():
        r = SC.kafka_units(**v)
        rows.append([g, r["type"], f"{r['planned']:,}", ", ".join(f"{n} {u}" for n, u in r["by_limit"].items()), str(r["units"])])
    b.table(["Group", "Type", "Planned partitions", "Units needed by", "Units"], rows,
            caption="Calculator example: Confluent capacity units (illustrative inputs)", widths=[1.8, 2.4, 2.6, 7.8, 2], size=8.5)
    rows = []
    for s, v in SC.OS_EXAMPLE.items():
        r = SC.opensearch(**v)
        rows.append([s, f"{r['primary_gib']}", f"{r['storage_gib']}", str(r["shards"]), str(r["nodes_storage"]), str(r["nodes_shards"]), str(r["nodes"])])
    b.table(["Service", "Primary GiB", "Storage GiB", "Shards", "Nodes by storage", "Nodes by shards", "Data nodes"], rows,
            caption="Calculator example: OpenSearch data nodes (illustrative inputs)", widths=[2.4, 2.2, 2.2, 2, 2.6, 2.6, 2.6], size=8.5)
    b.p("The workbook formulas were checked by recalculating the workbook in LibreOffice Calc and comparing every output "
        "with the Python functions that produce these tables. Recheck the constants on the vendor pages before each use.")


ALERTS = [
    ["Stream service status", "Pega (Stream landing page, alerts)", "Not NORMAL", "P1 in PROD", "Section 18.2"],
    ["Queue backlog", "Pega Admin Studio", "Ready to process grows for longer than the agreed period", "P2", "Check batch tier and consumer errors"],
    ["Broken queue items", "Pega Admin Studio", "Above zero for business-critical processors", "P2", "Investigate and requeue"],
    ["Delayed queue items", "Pega Admin Studio", "Growing for longer than 15 minutes", "P2", "Check Kafka reachability (DF-01, Section 9.8)"],
    ["Search indexer broken items", "Pega Admin Studio, `pySASIncrementalIndexer` [R70]", "Above zero", "P2", "Read the error type; fix; requeue (DF-06 to DF-08)"],
    ["Lag drain time against retention", "Lag and consume rate from the Metrics API [R56]; `retention.ms` (DP-5)", "Time to drain the lag above 25 % of the topic retention", "P1", "Add consumers within the partition count; stop the cause (DF-05)"],
    ["Consumer lag and request errors per principal", "Confluent Metrics API [R56]", "Lag above baseline; authentication or authorization errors", "P2", "Section 18.2"],
    ["Client throttling", "Metrics API `client_limit_milliseconds` by principal [R56]", "Above zero for 5 minutes", "P2", "Find the limit hit ({ref:tab_cc_limits})"],
    ["Connections per cluster", "Confluent Metrics API [R56]", "Above 70 % of the cluster's connection limit", "P3", "Capacity review"],
    ["Partition count per cluster", "Confluent Metrics API", "Above 70 % of the cluster limit", "P3", "Capacity review (Section 6.7)"],
    ["Throughput per service account", "Confluent Metrics API [R36]", "At quota for longer than 15 minutes", "P3", "Review quota or schedule"],
    ["SRS errors, latency and restarts", "SRS logs; pod metrics", "Above baseline; any restart loop", "P2", "Section 18.3"],
    ["OpenSearch health", "Provider metrics", "Yellow for longer than 30 minutes; red at once", "P2 / P1", "Section 18.3"],
    ["OpenSearch disk", "Provider metrics", "Above the low watermark less 10 points", "P2", "Add storage"],
    ["Okta token failures", "Pega log; Okta System Log", "Any repeated failure", "P2", "Section 18.3"],
    ["Okta rate limit", "Okta System Log warning and violation events [R52]", "Any warning; any violation", "P2 / P1", "Find the caller; Section 7.6"],
    ["Pod health", "Managed Prometheus", "OOMKilled, restart loop, HPA at maximum for 15 minutes", "P2", "Section 10.2"],
    ["Zone spread", "Managed Prometheus", "More than half of a tier's pods in one zone", "P3", "Section 4.6"],
    ["Long GC pauses", "GC log", "Pauses above 2 seconds, or GC time above 10 % of an interval", "P3", "Heap review"],
    ["External secret sync", "External Secrets Operator status", "Any ExternalSecret not SecretSynced", "P2", "Section 8"],
    ["Certificate expiry", "Synthetic checks", "Less than 30 days", "P3", "Renew (Section 8.4)"],
    ["Private DNS resolution", "Synthetic checks", "A public IP or no answer", "P2", "Section 4.4"],
]


def s18_observability(b):
    b.h1("Observability, monitoring and logging")
    b.p("Kafka and search now run outside Pega, on three vendors' services. A fault can start in any of them and show up "
        "as a slow screen in Pega. Observability here means collecting enough telemetry from every layer, with the same "
        "environment label and the same clock, to find the layer at fault within minutes. {ref:fig_observability} shows the "
        "design.")
    b.figure(GEN + "fig_observability.png", "Telemetry sources, collection, stores and use", OWN, width_cm=16.5, label="observability")

    b.h2("Telemetry sources")
    b.table(["Source", "Telemetry", "Collection", "Store", "Notes"], [
        ["Pega web and batch pods", "PegaRULES and ALERT logs on stdout; GC log file", "Azure Monitor agent container log collection [R60]", "Log Analytics", "GC file tailed by the agent [R23]"],
        ["Pega Platform", "Health, alerts, exceptions, guardrail data", "Pega Diagnostic Center [R51]", "PDC", "Section 19.3"],
        ["AKS", "Node, pod, HPA and control-plane metrics", "Managed Prometheus [R60]", "Azure Monitor workspace", "Grafana dashboards"],
        ["Confluent Cloud", "Throughput, requests, connections, lag, throttling, by principal", "Metrics API `/export` endpoint in Prometheus format, scraped every minute [R56]", "Azure Monitor workspace", "Needs a Cloud API key for a service account with the MetricsViewer role. The Metrics API addresses are not static, so allow it by FQDN"],
        ["Confluent audit log", "Authentication, ACL and management events", "Consumer on topic `confluent-audit-log-events` in the audit log cluster [R57]", "SIEM", "Kept 7 days by default; export for longer retention"],
        ["OpenSearch", "Cluster health, nodes, disk, latency; slow logs; audit logs", "Provider export", "Log Analytics", "Section 19.2"],
        ["SRS pods", "Application logs on stdout", "Azure Monitor agent", "Log Analytics", "Request errors and latency"],
        ["Okta", "System Log: token issue, failures, rate-limit events", "Okta log streaming or System Log API to the SIEM", "SIEM", "Rate-limit events [R52]"],
        ["Azure Firewall", "Allowed and denied flows", "Diagnostic settings", "Log Analytics", "IT-09, IT-10 evidence"],
        ["Synthetic checks", "DNS, TLS, Kafka metadata, SRS and token checks", "CronJob per namespace", "Log Analytics and metrics", "Section 19.6"],
    ], caption="Telemetry sources", widths=[2.6, 3.6, 4, 2.4, 4], size=8)

    b.h2("Logging design")
    b.bullets([
        "**One label everywhere.** The namespace carries the environment code (`pega-<code>`, `srs-<code>`). Add the code as a label to Confluent and OpenSearch metrics at scrape time, so a dashboard can filter one environment on a shared group.",
        "**Workspaces.** Use one Log Analytics workspace for non-production and one for production. Production logs never go to a non-production workspace. Set retention per the customer's policy, for example 30 days interactive in non-production and 90 days in production with archive after that.",
        "**Log levels.** Keep Pega and SRS at their default levels in PROD. Raise a level for one logger and one pod for a set time when Pega Support asks, then return it. A custom `prlog4j2` file can be supplied through the chart if the default layout does not suit the log platform [R23].",
        "**Sensitive data.** Non-production logs come from masked clones only. Never log the JAAS value, tokens or private keys; the pipeline secret scan covers values files, and log queries for `password=` and `Bearer ` run weekly, together with queries for the customer's personal data patterns (DT-10). Slow logs and heap dumps follow the rules in Section 9.6.",
        "**OpenSearch slow logs.** Use the cluster-level search request slow log, available from OpenSearch 2.12, rather than per-index shard slow logs [R58]. It needs no change to index settings, which SRS owns (Section 7.4).",
        "**Confluent audit log.** The default 7-day retention is too short for incident review [R57]. Stream it to the SIEM.",
    ])

    b.h2("Pega Diagnostic Center")
    b.p("Pega Diagnostic Center (PDC) collects health and alert data from Pega and shows it per system. For a client-managed "
        "deployment, the endpoint URL that PDC provides is entered in Pega at Configure > System > Settings. Data goes one "
        "way, from Pega to PDC, over HTTPS, and the JVM truststore must trust the PDC certificate chain [R51].")
    b.bullets([
        "Register each environment as its own system in PDC, so production and non-production alerts are never mixed.",
        "A clone carries production's PDC setting (CD-16). Change it during run F, before any alert is sent.",
        "Allow the PDC endpoint at the hub firewall from the Pega subnets (NW-4).",
        "Use PDC for Pega-level analysis (alerts such as PEGA0179, exceptions, guardrails) and the Azure stack for platform and service telemetry. Both are needed; neither replaces the other.",
    ])

    b.h2("Dashboards")
    b.table(["Dashboard", "Scope", "Panels", "Users"], [
        ["Environment overview", "One per environment", "M1 response times; pod health; stream status; queue backlog; search errors; token failures", "Operations, test leads"],
        ["Kafka group", "One per cluster (NP1, NP2, PROD)", "Throughput, requests, connections, lag and throttling by service account; partitions against limit", "Kafka team"],
        ["Search group", "One per OpenSearch service", "Health, disk against watermarks, latency, indexing rate, shards per node; SRS errors by environment", "Search team"],
        ["Identity", "Okta org", "Token requests per client, failures, rate-limit events", "Identity team"],
        ["Capacity", "All groups", "Units, partitions, shards, disk, node usage against plan; quarterly review", "Platform lead"],
        ["Cutover", "PROD during cutover and hypercare", "Steps C-1 to C-10 timings; index build progress; backlog; error rates", "Cutover manager"],
    ], caption="Dashboards", widths=[3, 3.4, 7.2, 3], size=8.5)

    b.h2("Alerts and thresholds")
    b.p("Thresholds marked as baselines come from the PERF load test. Route PROD P1 alerts to on-call at any hour, NP2 alerts "
        "to the test lead during test windows, and NP1 alerts during business hours. An alert on a shared cluster or search "
        "service goes to the owner of that service, with the environment label in the message.")
    b.table(["Signal", "Source", "Threshold", "Severity", "Response"], ALERTS,
            caption="Alerts, thresholds and responses", widths=[3.2, 3.6, 4.4, 1.6, 3.8], size=8, label="alerts")

    b.h2("Synthetic checks")
    b.p("A CronJob in each `pega-<code>` namespace runs a subset of the Appendix C checks and publishes each result as a "
        "metric, so a broken path is found before users find it.")
    b.table(["Check", "Commands", "Interval", "Alert when"], [
        ["Confluent DNS and TLS", "K-1, K-2", "5 minutes", "A public IP, no answer, or a TLS failure"],
        ["Kafka metadata", "K-3 with the environment's own key", "5 minutes", "Any broker missing or unreachable"],
        ["SRS", "S-5 health call", "5 minutes", "Unhealthy or no answer"],
        ["Okta token", "O-1", "15 minutes, to limit token requests", "Token not issued"],
        ["Certificate expiry", "Read the chains from K-2 and S-5", "Daily", "Less than 30 days"],
    ], caption="Synthetic checks", widths=[3.4, 4.4, 3.6, 5.2], size=8.5)

    b.h2("Following an incident across services")
    b.p("Each system names the same environment differently. {ref:tab_ids} lists the identifiers to search for, so an "
        "engineer can follow one incident from a Pega log line to the Confluent, OpenSearch and Okta records.")
    b.table(["System", "Identifier for the environment", "Identifier for the request or client"], [
        ["Pega", "Namespace `pega-<code>`; node ID in the log", "Thread and requestor in PegaRULES log"],
        ["Confluent", "Service account `sa-pega-<code>` (`principal_id` in metrics and audit log)", "Topic and consumer group under `pega-<code>-`"],
        ["SRS", "Namespace `srs-<code>`", "Index prefix `pega26-<code>`"],
        ["OpenSearch", "User `pega26-<code>-srs`", "Index name in slow and audit logs"],
        ["Okta", "Client `pega-srs-<code>`", "Client ID in System Log events"],
        ["Azure", "Subnet and pod IP", "Firewall flow log"],
    ], caption="Identifiers used to correlate one environment across systems", widths=[2.6, 7, 7], size=8.5, label="ids")
    b.steps([
        "Start from the time and environment of the first symptom. All sources use UTC.",
        "Check the environment overview dashboard to find the first layer that changed: M2 to M6 in that order.",
        "Search that layer's logs with the identifiers above for the five minutes before the symptom.",
        "If the layer is a shared service, check the group dashboard for other environments affected at the same time. One environment affected points to its own configuration or load; all environments point to the service.",
        "Record the timeline in the incident, with links to the queries used.",
    ])
