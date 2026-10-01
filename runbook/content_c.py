"""Sections 10 to 12: upgrade strategy, Kafka topic migration, search index migration."""
from content_a import GEN, PUB, OWN


def s10_upgrade(b):
    b.h1("Upgrade strategy from Pega 8.8 to 26.1.1")
    b.h2("What changed between 8.8 and 26.1.1")
    b.table(["Release", "Change that affects this programme", "Source"], [
        ["8.8", "Embedded Kafka, Elasticsearch and Cassandra deprecated. VM-based deployment deprecated. Stream tier (nodeType Stream) deprecated.", "[R2, R30]"],
        ["'24.1", "Last release that supports both embedded services and VM-based deployments.", "[R2]"],
        ["'24.2", "External Kafka, external search and (for CDH and Process AI) external Cassandra required. Embedded Elasticsearch and the plug-in removed.", "[R2, R16]"],
        ["Patches 23.1.4, 24.1.3, 24.2.2 and later", "Hazelcast removal tooling: HazelcastDecommission service package and the prconfig/cluster/hazelcast/disabled/default DSS.", "[R5, R9]"],
        ["'25", "Containerized deployment only. Hazelcast removed. Tomcat 10.1 (Jakarta EE 9) only. All tables need primary keys.", "[R2, R4]"],
        ["'26", "Kafka client 4.0.0 (backward compatible with 3.9.2). Partitioned, multi-threaded queue processing (PEGA0179). SystemPulse topic with 6 partitions. Cassandra 5.0 support.", "[R3]"],
    ], widths=[3.2, 11.4, 2], caption="Changes between 8.8 and 26.1.1 that affect Kafka, search and the update path", size=9)
    b.h2("Why 8.8 cannot be updated directly")
    b.p("Pega requires Hazelcast to be removed before an update to '25 or later [R5]. The removal needs functions that exist "
        "only in patches 23.1.4, 23.1.5, 24.1.3, 24.1.4, 24.2.2, 24.2.3 and later [R9]. Pega 8.8 has neither the "
        "HazelcastDecommission service package nor the DSS behavior, so it cannot remove Hazelcast, and therefore cannot be "
        "updated straight to 26.1.1. The system must pass through a bridge release.")
    b.callout("evidence", "Pega's page \"Adopting Pega Platform infrastructure changes\" gives the sequence for clients on older releases: update to the latest patch of '24.1, externalize Elasticsearch, Kafka and (if used) Cassandra, remove Hazelcast, shift from virtual machines to containers, then update to '25 [R2]. The '26 prerequisites page repeats that Hazelcast must be removed before updating to '25 or later [R3].")
    b.h2("Release plan")
    b.figure(GEN + "fig_decision_source_path.png", "Assessing the 8.8 source for Release 1", OWN, width_cm=11)
    b.table(["", "Release 1: externalize on 8.8", "Release 2: platform move", "Release 3: update to 26.1.1"], [
        ["Pega version", "8.8 (unchanged)", "8.8 to bridge ('24.1 latest patch)", "Bridge to 26.1.1"],
        ["Runtime", "Current 8.8 servers", "New AKS cluster", "Same AKS cluster"],
        ["Kafka", "Current stream to Confluent (drain first)", "Same Confluent cluster, new prefix", "Same topics"],
        ["Search", "Current search to SRS (full build)", "Same SRS, new customerDeploymentId (full build)", "Same indexes"],
        ["Hazelcast", "Unchanged", "Removed with the DSS method", "Absent"],
        ["Database", "Unchanged", "Copied to Azure and updated in place", "Zero-downtime update (new rules schema)"],
        ["Outage", "Yes: drain, restart, index build", "Yes: drain, copy, update, index build", "Near zero (rolling restart)"],
        ["Rollback", "Point 8.8 back to the old stream and search", "Keep 8.8 and its database; revert DNS", "Restore pre-update backup (Section 15.4)"],
    ], widths=[2.4, 4.6, 4.8, 4.8], caption="What each release changes", size=8.5, first_col_bold=True)
    b.h3("Choice of bridge release")
    b.p("The bridge release is a transit point, used only until Release 3. This design uses the latest '24.1 patch, at least "
        "24.1.4, for three reasons. Pega names '24.1 in its adoption sequence [R2]. Patch 24.1.4 includes the Hazelcast removal "
        "changes without a hotfix, whereas 24.1.3 needs HFIX-C2252 [R7]. And '24.1 still accepts the embedded services the "
        "8.8 estate may use, which keeps the rehearsal of Release 2 independent of Release 1 timing. Because Release 1 removes "
        "the embedded services first, the latest '24.2 patch (24.2.3 or later) is also a valid bridge; OD-02 records the choice "
        "and asks Pega Support to confirm the supported path from the selected bridge to 26.1.1.")
    b.h3("Update method and staging")
    b.p("Pega's guidance is to update a staging environment first and to test there before production [R25, R26]. The "
        "zero-downtime checklist adds that copying production data into staging is not recommended; staging should hold "
        "appropriate test data [R25]. Rehearsal timings for drain, copy, update and index build only mean something if the "
        "volumes are close to production, so OD-13 asks the customer to decide between masked production-scale data and a "
        "synthetic data set of the same size.")
    b.h2("Preparation on 8.8 (all releases)")
    b.table(["#", "Task", "How", "Output", "Needed before"], [
        ["P-1", "Run the Pega Upgrade Tools against 8.8", "Pega Upgrade Tools for the target release [R11]", "List of impacted rules, CodeSets and JARs", "Release 2 rehearsal"],
        ["P-2", "Prepare Jakarta EE versions of custom JARs", "Rebuild against jakarta.* packages; Pega notes that not every javax.* package maps to jakarta.* [R11]", "New JARs held in the artifact repository", "Release 3 rehearsal"],
        ["P-3", "Set each impacted CodeSet DSS version to latest", "Supported from 8.8 [R11]", "DSS change record", "Release 3"],
        ["P-4", "Scan for missing primary keys", "primaryKeyUtility dry run; check database free space, because the utility copies tables [R12]", "Report of tables without primary keys", "Release 2 rehearsal"],
        ["P-5", "Create missing primary keys", "primaryKeyUtility (non-dry run) in a maintenance window", "Utility log", "Release 3"],
        ["P-6", "Review custom queue processors", "Inventory and test plan for the '26 partitioned processing model; remove DSS delayeditems/dataflowbased/threadspernode [R3]", "Queue processor test cases", "Release 3 rehearsal"],
        ["P-7", "Confirm database support", "Platform Support Guide for 26.1.1 [R1]", "Engine and version confirmed", "Release 2 design"],
        ["P-8", "Inventory Kafka data sets and integrations", "Section 11.3", "Integration list with owners", "Release 1 design"],
        ["P-9", "Measure searchable data", "Search landing page and database counts per indexed class", "Baseline for sizing and V-S checks", "Release 1 design"],
        ["P-10", "Resolve broken queue items", "Admin Studio, queue processors, Broken items", "Backlog near zero", "Each cutover"],
    ], widths=[1, 3.6, 5.6, 3.6, 2.8], caption="Preparation tasks", size=8.5)
    b.h2("Release 1: externalize Kafka and search on 8.8")
    b.p("Release 1 changes only the stream provider and the search provider. Pega's '26 Kafka and search pages have 8.8 "
        "versions (select 8.8 in the documentation version list), and SRS supports 8.6 and later [R13, R16]. Section 11.6 and "
        "Section 12.6 hold the detailed steps; {ref:fig_release1} shows the order.")
    b.figure(GEN + "fig_release1_flow.png", "Release 1 sequence: drain, switch and rebuild on 8.8", OWN, width_cm=10.5, label="release1")
    b.callout("note", "If the 8.8 nodes run on VMs outside Azure, Release 1 needs private routing from those servers to the Confluent private endpoints and to SRS (for example ExpressRoute or VPN into the hub VNet). SRS has no ingress in the target design, so Release 1 needs an internal load balancer for SRS that only the 8.8 server subnets can reach. Remove it after Release 2.")
    b.h2("Release 2: platform move to AKS on the bridge release")
    b.h3("Sequence")
    b.steps([
        "Drain the 8.8 queues with the Stream Migration activity, then stop all 8.8 nodes (Section 11.6).",
        "Take the final database backup and restore it to the Azure database.",
        "Run the installer job with the bridge installer image, `global.actions.execute: upgrade` and `installer.upgrade.upgradeType: in-place` [R28].",
        "Deploy the bridge tiers (`global.actions.execute: deploy`) with the new streamNamePattern prefix and the new customerDeploymentId. Use embedded Hazelcast settings (hazelcast.enabled false, clusteringServiceEnabled false) [R28].",
        "Remove Hazelcast with the downtime method (Section 10.6.2).",
        "Run the full index build through SRS (Section 12.6).",
        "Run smoke tests, then switch DNS (Section 14).",
    ])
    b.h3("Hazelcast removal with the DSS method")
    b.p("Before the window, confirm the Pega prerequisites: database CPU at least 10 % below its alert threshold, Kafka "
        "capacity for about 100 extra partitions for the environment, and Kafka CPU at least 15 % below its alert threshold [R6]. "
        "Pega also advises scaling down to the minimum number of nodes [R8].")
    b.table(["Step", "Action [R8]", "Expected result"], [
        ["H-1", "Dev Studio > Records > SysAdmin > Dynamic System Settings. Find prconfig/cluster/hazelcast/disabled/default. If it is missing, create it with owning ruleset Pega-Engine, type String, and select \"Is restart required\".", "DSS exists"],
        ["H-2", "Set its value to true and save.", "Value true"],
        ["H-3", "Stop all Pega nodes (scale every tier to 0 replicas).", "No Pega pods running"],
        ["H-4", "Start all Pega nodes (restore replica counts).", "All pods Ready"],
        ["H-5", "Skip Clustering Service removal: the bridge runs embedded Hazelcast. (If the Clustering Service was used, set hazelcast.enabled and clusteringServiceEnabled to false and run helm upgrade.)", "No Clustering Service pods"],
        ["H-6", "Records > Integration-Resources > Service Package > HazelcastDecommission. Run hazelcast/disabled with GET.", "Response true"],
        ["H-7", "Run checkRemoteExecutionConnectivity with GET.", "Response allNodesReachable [R7]"],
    ], widths=[1.2, 11, 4.4], caption="Hazelcast removal steps on the bridge release", size=8.5)
    b.h2("Release 3: zero-downtime update to 26.1.1")
    b.p("Release 3 runs on the platform built in Release 2. The Pega Helm chart's zero-downtime upgrade type migrates the "
        "rules into a new rules schema, uses a temporary data schema, upgrades the rules, performs a rolling reboot onto the new "
        "rules, then upgrades the data schema [R28, R33]. It is supported for updates from 8.4.2 and later [R28]. Pega's update "
        "procedure for client-managed deployments has four parts: prepare the environment, update the database schemas, "
        "update the nodes with the Helm chart, and complete the post-update tasks [R27].")
    b.figure(GEN + "fig_stage2_flow.png", "Release 3 sequence on the AKS platform", OWN, width_cm=9.5)
    b.figure(GEN + "fig_zdt_schemas.png", "Schema states during a zero-downtime update",
             "Source: Pega Helm charts, \"Upgrading Pega Platform in your deployment with zero-downtime\" [R33]. © Pegasystems Inc., Apache License 2.0. Images combined and numbered for this document.",
             width_cm=16)
    b.code("""global:
  actions:
    execute: "upgrade-deploy"
installer:
  image: "<acr-name>.azurecr.io/platform/installer:26.1.1"
  upgrade:
    upgradeType: "zero-downtime"
    targetRulesSchema: "<new-rules-schema>"
    targetDataSchema: "<temp-data-schema>"
""", title="values-<env>.yaml: installer section for Release 3 [R28]")
    b.table(["Step", "Action", "Source"], [
        ["U-1", "Confirm Hazelcast removal (H-6 and H-7 results from Release 2).", "[R7, R8]"],
        ["U-2", "Update SRS to the image version listed for the Helm chart that deploys 26.1.1; confirm the search cluster version is on the matrix.", "[R16, R29]"],
        ["U-3", "Confirm Confluent compatibility with the Kafka 4.0.0 client in staging (V-K-05).", "[R3]"],
        ["U-4", "If topic creation is restricted, set SystemPulse_SystemPulseTopicName to 6 partitions.", "[R3]"],
        ["U-5", "Remove DSS delayeditems/dataflowbased/threadspernode; retest custom queue processors.", "[R3]"],
        ["U-6", "Confirm primary keys exist on all tables (P-5).", "[R12]"],
        ["U-7", "Update the Helm values: 26.1.1 images, installer section above. Run helm upgrade.", "[R28, R33]"],
        ["U-8", "After the update, import the Jakarta EE JARs into a higher CodeSet version and restart.", "[R11]"],
        ["U-9", "Configure prpcUtils for Kafka if pipelines use it.", "[R10]"],
        ["U-10", "Run the post-update checks: Stream landing page, index status, queue processors, regression pack.", "[R15, R21]"],
        ["U-11", "Drop the temporary data schema after the update, as the Helm README instructs.", "[R28]"],
    ], widths=[1.2, 13.2, 2.2], caption="Release 3 steps", size=8.5)


def s11_kafka_migration(b):
    b.h1("Kafka topic migration: requirements, validation, strategy and execution")
    b.h2("Requirements")
    b.table(["ID", "Requirement", "Source"], [
        ["R-K-01", "No message that is in transit in a Pega stream queue at the time of a provider switch may be lost.", "[R15]"],
        ["R-K-02", "Every queue processor and data flow that holds messages must be RUNNING when the drain starts, because the Stream Migration activity does not drain STOPPED, FAILED or NOT RUNNING ones.", "[R15]"],
        ["R-K-03", "The target Kafka must meet Pega's settings, ACLs and authentication rules before the first start.", "[R13]"],
        ["R-K-04", "Pega must report Provider ExternalKafka and Status NORMAL on the Stream landing page after each start.", "[R15]"],
        ["R-K-05", "Topic names must carry an environment-specific prefix so environments sharing a cluster cannot read each other's data.", "[R13, R28]"],
        ["R-K-06", "Application Kafka integrations (Kafka data sets) must keep working, or be repointed with an agreed offset position.", "[R13]"],
        ["R-K-07", "The source topics must remain intact until the rollback window for each release closes.", "AD-05"],
    ], widths=[1.6, 12.8, 2.2], caption="Kafka migration requirements", size=9)
    b.h2("What can and cannot be migrated")
    b.p("Pega states that existing Stream data cannot be moved to a new Kafka storage, whether the source is embedded stream "
        "or another external Kafka, because of how each solution stores data [R15]. The Helm chart guidance says the same for "
        "the stream tier: existing stream data is not migrated [R30]. What Pega offers instead is a controlled drain: the Stream "
        "Migration activity empties the queues so that no in-transit message is lost when the provider changes [R15].")
    b.table(["Kafka content", "Can it be copied?", "Treatment"], [
        ["Queue processor messages (standard and dedicated)", "No", "Drain on the source; target starts with empty topics"],
        ["Delayed queue processor items", "No", "Drain; items scheduled far in the future must be checked on the source before the drain (V-K-03)"],
        ["Data flow stream partitions fed by the stream service", "No", "Drain; compare last processed IDs with topic end offsets [R30]"],
        ["Stream data sets (application)", "No", "Producers stopped; consumers finish; target topics start empty"],
        ["Consumer group offsets for Pega topics", "Not needed", "New topics, new offsets"],
        ["Kafka data sets on a separate Kafka service", "Not part of the stream service", "Decision in {ref:fig_stream_data}"],
    ], widths=[5.2, 3.2, 8.2], caption="Treatment of each kind of Kafka content", size=9)
    b.h2("Inventory")
    b.p("Build the inventory in staging and confirm it in production before each release. Record it in Appendix A.")
    b.table(["Inventory item", "Where to find it", "Recorded fields"], [
        ["Queue processors", "Admin Studio > Queue processors", "Name, type, status, Ready to process, Broken, node type"],
        ["Job schedulers", "Admin Studio > Job schedulers", "Name, node type, schedule"],
        ["Data flows reading streams", "Data Flow landing page", "Name, run ID, status, partitions"],
        ["Kafka data sets and Kafka configuration instances", "Records > Data Model > Data Set (type Kafka); Records > SysAdmin > Kafka", "Name, brokers, topic, owner, consumer group"],
        ["Topics on the target", "Confluent CLI or console (command K-4)", "Name, partitions, replication, max.message.bytes"],
    ], widths=[4.4, 6, 6.2], caption="Kafka inventory", size=9)
    b.h2("Strategy")
    b.figure(GEN + "fig_decision_stream_data.png", "Decision: treatment of each topic or stream", OWN, width_cm=13.5, label="stream_data")
    b.table(["Release", "Kafka strategy", "Why"], [
        ["Release 1", "Drain the 8.8 stream with the Stream Migration activity, stop all nodes, configure Confluent, start. Topics are created under `pega-<env>-` on Confluent.", "Pega documented procedure [R15]; no Pega software change at the same time [R30]."],
        ["Release 2", "Drain again with the activity, stop 8.8, update the copied database, start the bridge release with prefix `pega-<env>2-` on the same Confluent cluster.", "The new prefix gives the bridge empty topics and leaves the 8.8 topics untouched for rollback (AD-05)."],
        ["Release 3", "No drain. The zero-downtime update keeps the same prefix and topics.", "Same Kafka cluster; Pega performs a rolling reboot [R28]."],
    ], widths=[2.2, 8.8, 5.6], caption="Kafka strategy per release", size=9)
    b.h3("Application Kafka data sets")
    b.p("Kafka data sets belong to the application, not to the platform. Pega requires them to use a Kafka service separate "
        "from the stream service [R13]. For each one, the application owner chooses one of these options:")
    b.bullets([
        "**Keep the current Kafka service.** Only the network path from AKS changes. Confirm reachability and credentials in Release 2.",
        "**Move to a separate Confluent cluster, new records only.** The consuming data flow starts from new records after cutover; record the last offsets on the source as evidence.",
        "**Move to a separate Confluent cluster with history.** Use Confluent Cluster Linking: mirror topics copy messages byte for byte and keep partition and offset positions, and consumer offsets can be synchronized [R41]. Promote the mirror topics at cutover.",
        "**Replay from the system of record.** Use when the source cannot be linked and history is needed.",
    ])
    b.h2("Validation matrix")
    b.table(["ID", "When", "Check", "Method", "Pass criterion", "Evidence"], [
        ["V-K-01", "Before", "Target reachable from Pega pods", "Commands K-1 to K-3 (Appendix D)", "Private IPs; TLS chain valid; all brokers listed", "Command output"],
        ["V-K-02", "Before", "ACLs present", "confluent kafka acl list", "Four ACL entries per {ref:tab_acls}", "ACL export"],
        ["V-K-03", "Before", "Queues healthy", "Admin Studio queue processors", "All in scope RUNNING; Broken items resolved or accepted in writing", "Screenshot and list"],
        ["V-K-04", "During", "Drain complete", "GET .../pzstream/migration", "queueSize 0, timeToDrainMS 0, migrationStatus COMPLETED [R15]", "JSON response with time"],
        ["V-K-05", "After start", "Client compatibility", "Pega log on start; produce and consume test queue item", "No client-broker version errors; test item processed", "Log extract"],
        ["V-K-06", "After start", "Stream service healthy", "Configure > Decisioning > Infrastructure > Services > Stream", "Provider ExternalKafka; Status NORMAL [R15]", "Screenshot"],
        ["V-K-07", "After start", "Topic and ACL coverage", "Command K-4; compare with ACL prefix", "Every Pega-created topic under an allowed prefix or literal ACL", "Topic list"],
        ["V-K-08", "After start", "Message size limit", "Command K-6 on each topic", "max.message.bytes 5,000,000 or higher", "Config output"],
        ["V-K-09", "After start", "Queue processors running", "Admin Studio", "All expected queue processors RUNNING; Ready to process falling", "Screenshot"],
        ["V-K-10", "After start", "Partition budget", "Command K-5", "Total within limit with 30 % headroom", "Count"],
        ["V-K-11", "After start", "Application Kafka data sets", "Run each data set test or data flow", "Expected messages received at expected offsets", "Data flow run report"],
        ["V-K-12", "After rollback window", "Old topics removed", "Command K-4 for the old prefix", "No topics under the retired prefix", "Topic list"],
    ], widths=[1.5, 1.7, 2.8, 3.8, 4.4, 2.4], caption="Kafka validation matrix", size=8)
    b.h2("Execution")
    b.table(["Step", "Action", "Command or location", "Expected result"], [
        ["K-E1", "Confirm V-K-01 to V-K-03 pass.", "Appendix D", "All pass"],
        ["K-E2", "Stop producers: route users to a maintenance page, stop listeners and file or email services, pause producer data flows. Do not stop consumers.", "Ingress maintenance rule; Admin Studio", "No new items being queued"],
        ["K-E3", "Start the Stream Migration activity from inside a Pega pod.", "`curl --request POST http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration` [R15]", "HTTP success"],
        ["K-E4", "Poll the status every minute.", "`curl --request GET http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration` [R15]", "queueSize falls to 0; migrationStatus COMPLETED"],
        ["K-E5", "Stop all Pega nodes.", "Scale tiers to 0 (AKS) or stop servers (VMs)", "No nodes running"],
        ["K-E6", "Configure the target Kafka settings (Section 7.7).", "Helm values or 8.8 stream settings", "Configuration reviewed"],
        ["K-E7", "Start all nodes.", "helm upgrade or server start", "Pods Ready"],
        ["K-E8", "Run V-K-05 to V-K-11.", "Section 11.5", "All pass"],
        ["K-E9", "Only when switching between two external providers: restart the Kafka queues.", "`curl --request DELETE http://localhost:8080/prweb/PRRestService/CloudRemoteAPI/v1/pzstream/migration` [R15]", "HTTP success; queues restarted"],
        ["K-E10", "Re-enable producers.", "Remove maintenance rule; restart listeners", "New items processed"],
    ], widths=[1.4, 5.6, 6.2, 3.4], caption="Kafka execution steps", size=8)
    b.figure(PUB + "pega_docs_stream-migration-external-kafka-status.png", "Stream landing page after the switch: Provider ExternalKafka, Status NORMAL",
             "Source: Pega Documentation, \"Switching Kafka providers while preserving Stream data\" [R15]. © Pegasystems Inc. Reproduced with attribution.",
             width_cm=14)
    b.callout("caution", ["The REST call uses localhost, so run it from inside a Pega node (for example kubectl exec into a batch pod). Run it once, from one node.",
              "If the 8.8 source runs the deprecated stream tier on Kubernetes, the Helm chart describes an equivalent manual drain: set producing tiers to 0 replicas, wait until Ready to Process is 0 for every queue processor, and compare data flow partition last IDs with topic offsets from GetOffsetShell [R30]. Use it as a cross-check of the activity result."])
    b.h3("Release 3 Kafka points")
    b.bullets([
        "Pega '26 replaces single-threaded queue processing with a partitioned model with isolated thread pools per processor [R3]. Expect different consumer group activity on Confluent after the update; compare throughput, not thread counts.",
        "If dynamic topic creation is allowed, Pega raises SystemPulse_SystemPulseTopicName to 6 partitions itself; otherwise do it before the update [R3].",
        "Confirm the Confluent cluster accepts the Kafka 4.0.0 client used by '26. Pega warns that a broker older than the client library can cause failures or slow client-broker communication [R3].",
    ])


def s12_search_migration(b):
    b.h1("Search index migration: requirements, validation, strategy and execution")
    b.h2("Requirements")
    b.table(["ID", "Requirement", "Source"], [
        ["R-S-01", "After each release, every indexed class (Work, Data, Rules and custom indexes) must be searchable with results that match the database.", "[R21]"],
        ["R-S-02", "The search cluster must be on the SRS compatibility matrix and configured with the two required cluster settings.", "[R16]"],
        ["R-S-03", "Each Pega environment must use its own immutable customerDeploymentId.", "[R17, R28]"],
        ["R-S-04", "Pega-to-SRS traffic must be authorized (OAuth) and encrypted (TLS or service mesh).", "[R16]"],
        ["R-S-05", "The 8.8 indexes must remain usable until the Release 2 rollback window closes.", "AD-06"],
        ["R-S-06", "The index build duration must fit inside the outage window, measured in rehearsal.", "[R17]"],
    ], widths=[1.6, 12.8, 2.2], caption="Search migration requirements", size=9)
    b.h2("What can and cannot be migrated")
    b.p("SRS builds its own indexes from the Pega database. After Pega connects to SRS, \"SRS indexes all searchable data, "
        "which requires a downtime period\" whose length depends on the data model, cluster resources, the number of queue "
        "processors and the amount of searchable data [R17]. Indexes from embedded search or the legacy plug-in are therefore "
        "not reused. Copying SRS indexes between search clusters with snapshots is also not used in this design, for two "
        "reasons: SRS owns index names and mappings, and Elasticsearch 8.x snapshots cannot be restored into OpenSearch, "
        "which can only restore snapshots from the versions before its fork, and supports moving later data only through "
        "reindexing tools [R43, R44].")
    b.figure(GEN + "fig_decision_search_index.png", "Decision: search index strategy", OWN, width_cm=15)
    b.h2("Inventory and baseline")
    b.table(["Item", "Where", "Recorded fields"], [
        ["Indexed classes and status", "Configure > System > Settings > Search, Indexing section, per tab [R21]", "Class, index type, status, document count"],
        ["Custom search indexes", "Search landing page; custom search properties rules", "Class, properties, owner"],
        ["Database row counts for indexed classes", "SQL count on each class table (DBA)", "Count with timestamp"],
        ["Index sizes on the search cluster", "Command S-4", "Index name, documents, size"],
        ["Key business searches", "Application team", "Search text, expected result count"],
    ], widths=[4.4, 6.6, 5.6], caption="Search inventory", size=9)
    b.h2("Strategy")
    b.table(["Release", "Search strategy", "Why"], [
        ["Release 1", "Deploy SRS and the search cluster; connect 8.8 to SRS; run the full index build.", "Pega documented path for moving to SRS [R17]."],
        ["Release 2", "Set a new customerDeploymentId; the bridge release builds a full new set of indexes on the same search cluster.", "Keeps the 8.8 indexes for rollback; SRS separates data by deployment ID [R16]."],
        ["Release 3", "Keep the customerDeploymentId; check index status after the update; re-index only classes that report a problem.", "Same SRS and indexes; zero-downtime update."],
    ], widths=[2.2, 8.4, 6], caption="Search strategy per release", size=9)
    b.h2("Validation matrix")
    b.table(["ID", "When", "Check", "Method", "Pass criterion", "Evidence"], [
        ["V-S-01", "Before", "Cluster version and health", "Commands S-1, S-2", "Version on the matrix; status green", "Output"],
        ["V-S-02", "Before", "Required settings", "Command S-3", "auto_create_index false; destructive_requires_name false", "Output"],
        ["V-S-03", "Before", "SRS healthy", "kubectl get pods -n srs-<env>; SRS logs", "All replicas Ready; no storage connection errors", "Output"],
        ["V-S-04", "Before", "Pega reaches SRS", "Command S-5 from a Pega pod", "TLS handshake succeeds", "Output"],
        ["V-S-05", "Before", "customerDeploymentId", "Helm values review", "Set explicitly; new value for Release 2", "Values diff"],
        ["V-S-06", "Before", "OAuth token content", "Decode a token from the IdP", "Scope pega.search:full granted; guid equals customerDeploymentId", "Decoded claims (no signature)"],
        ["V-S-07", "During", "Build progress", "Queue Processor landing page; system log [R19]", "Progress advancing; no growing broken items", "Screenshots"],
        ["V-S-08", "After", "Index status", "Search landing page [R21]", "No class in an error or CONFLICTS FOUND status", "Screenshot"],
        ["V-S-09", "After", "Document counts", "Search landing page counts against database counts", "Equal for Work and Data classes, or differences explained", "Comparison sheet"],
        ["V-S-10", "After", "Business searches", "Run the key searches", "Expected results returned", "Test record"],
        ["V-S-11", "After", "Incremental indexing", "Create and update a case; search for it", "Found within the agreed delay", "Test record"],
        ["V-S-12", "After rollback window", "Old indexes removed", "Command S-4 with the old prefix", "No indexes under the retired customerDeploymentId", "Output"],
    ], widths=[1.5, 1.6, 2.8, 4, 4.4, 2.3], caption="Search validation matrix", size=8)
    b.h2("Execution")
    b.table(["Step", "Action", "Where", "Expected result"], [
        ["S-E1", "Confirm V-S-01 to V-S-06 pass.", "Appendix D", "All pass"],
        ["S-E2", "Deploy or confirm SRS for the environment.", "helm upgrade --install with backingservices values", "SRS pods Ready"],
        ["S-E3", "Set pegasearch and global.customerDeploymentId in the Pega values (Section 8.7).", "Pega Helm values", "Values reviewed"],
        ["S-E4", "Start Pega. SRS begins indexing searchable data.", "helm upgrade", "Indexing queue items appear"],
        ["S-E5", "If an index needs a manual rebuild, open the Search landing page, select the index, click Re-index and choose the classes. The pxAccessSearchLP privilege is needed (PegaRULES:SysAdm4 includes it).", "Configure > System > Settings > Search [R20]", "Rebuild starts"],
        ["S-E6", "Monitor progress on the Queue Processor landing page and in the system log.", "[R19]", "Progress to completion"],
        ["S-E7", "If the build is slow and the database has headroom, tune DSS indexing/distributed/queue/maxrecords (records processed per invocation of the incremental indexer).", "Dynamic System Settings [R19]", "Higher throughput without database alerts"],
        ["S-E8", "Run V-S-07 to V-S-11.", "Section 12.5", "All pass"],
    ], widths=[1.4, 7.8, 4.2, 3.2], caption="Search execution steps", size=8)
    b.callout("note", ["Pega notes that reindexing individual classes leaves the state incomplete; a complete reindex is needed for the state to be available, and the system does not reindex child classes of a class you name [R20].",
              "Rebuilds of Work classes have the largest performance effect [R21]. Schedule manual rebuilds of large Work classes outside business hours after go-live."])
