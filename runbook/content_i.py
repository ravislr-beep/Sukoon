"""Section 9: data exchanged with Kafka, SRS, OpenSearch and Okta; classification, protection, retention and failure handling."""
from content_a import GEN, OWN


def s9_data(b):
    b.h1("Data flows, classification and protection")
    b.p("Externalizing Kafka and search moves Pega data out of the Pega nodes and onto two managed services that the "
        "customer does not operate. This section states what data actually leaves the database, how sensitive it is, how it "
        "is protected on each hop and in each store, how long it stays, how it is erased, and what happens to it when a "
        "transfer fails. Where Pega does not document a point, it becomes a Pega Support question (GQ-09 to GQ-11) or a data "
        "test (DT-01 to DT-12).")

    b.h2("What Pega exchanges with Kafka, SRS, OpenSearch and Okta")
    b.p("The Pega database remains the system of record. Kafka and OpenSearch hold copies or references, created by Pega "
        "for processing and for search. {ref:fig_data_flows} shows every hop and the highest class of data on it.")
    b.figure(GEN + "fig_data_flows.png", "Data flows and the highest data class on each hop", OWN, width_cm=16, label="data_flows")
    b.bullets([
        "**Queue processor messages (Kafka).** A producer queues work with Queue-For-Processing or the Run in Background shape. The message carries the producer's operator, access group, application and other context identifiers with the payload [R65]. For a page that has a `pzInsKey`, the default is to store the key only, and the consumer opens the record from the database. With \"Queue current snapshot of page\" selected, the message stores the entire page [R64]. Pages without a key are queued whole. The payload is therefore anything from a record key to a full case page.",
        "**Cluster messaging (Kafka).** From '25, Pega carries over Kafka the cluster messaging that Hazelcast used to carry [R7]. Pega does not publish what these messages contain (GQ-10).",
        "**Delayed and broken items (database).** Items waiting for a retry are held in `pr_sys_delayed_queue`, and items that failed after the last attempt in `pr_sys_msg_qp_brokenitems` [R66]. A broken item keeps the message, so it holds the same data as the Kafka message for as long as it is kept [R64].",
        "**Index documents (SRS to OpenSearch).** In SRS mode Pega indexes a limited set of predefined rule and data classes. For Work- classes only the classes and properties listed in the application's Relevant Records and in Custom Search Properties are indexed, unless DSS `indexer/srs/indexAllFieldsForFTS` is set [R68]. Custom search properties decide which properties are filterable, returnable and available for full-text search [R67]. Each indexed property is a copy of case data in OpenSearch.",
        "**Search requests and results (Pega to SRS).** Users type names, account numbers and other identifiers into search, and results return indexed values. Both cross the Pega-to-SRS hop and can appear in OpenSearch slow logs, which record slow queries [R58].",
        "**Tokens (Okta).** Pega authenticates with a signed client assertion and receives an access token with the scope and the `guid` claim (Section 7.6). Neither carries personal data, but a token is a credential until it expires.",
        "**Application Kafka data sets.** These read and write the customer's own topics on a separate Kafka service [R11]. Their content and classification belong to the data set owner (Section 12.3).",
    ])
    b.table(["ID", "Data item", "Where it is stored or carried", "Typical content", "Class"], [
        ["D-01", "Case and data records", "Pega database", "Business and personal data", "Restricted"],
        ["D-02", "Queue processor message, key only (default)", "Confluent topic `pega-<code>-*`", "Record key; operator, access group, application [R64, R65]", "Confidential"],
        ["D-03", "Queue processor message with page snapshot, or a page without a key", "Confluent topic", "Full clipboard page, which can include personal data [R64]", "Restricted"],
        ["D-04", "Delayed and broken items", "`pr_sys_delayed_queue`, `pr_sys_msg_qp_brokenitems` [R66]", "Same as D-02 or D-03, plus the error", "As D-02 or D-03"],
        ["D-05", "Cluster messaging", "Confluent topic", "Not published by Pega (GQ-10)", "Confidential until answered"],
        ["D-06", "Index documents", "OpenSearch `pega26-<code>*`; provider snapshots", "Indexed properties of cases and data [R67, R68]", "Restricted"],
        ["D-07", "Rule indexes", "OpenSearch", "Rule names and metadata", "Internal"],
        ["D-08", "Search terms and results", "Pega to SRS hop; OpenSearch slow logs [R58]", "Names and identifiers typed by users", "Restricted"],
        ["D-09", "Access tokens and client assertions", "Pega memory; Pega to Okta and SRS hops", "Client ID, scope, `guid`; no personal data", "Secret while valid"],
        ["D-10", "Credentials and keys", "Key Vault; Kubernetes secrets (Section 8.1)", "API keys, JAAS value, passwords, private keys", "Secret"],
        ["D-11", "Pega, SRS and GC logs", "Node disks; Log Analytics", "Exceptions, operator IDs, fragments of pages", "Confidential; Restricted if pages are logged"],
        ["D-12", "Heap dumps", "Node disks until copied", "Whole JVM memory: decrypted case data, tokens and secrets", "Restricted and Secret"],
        ["D-13", "Pega Diagnostic Center alerts", "Pega Diagnostic Center", "Alerts and exception details sent from the nodes [R51]", "Confidential"],
        ["D-14", "Confluent and OpenSearch audit logs", "Confluent audit log cluster [R57]; OpenSearch audit index [R77]", "Principals, IP addresses, actions", "Internal"],
    ], caption="Data inventory for Kafka and search", widths=[1.2, 3.6, 4.2, 5, 2.6], size=8, label="data_inventory")

    b.h2("Classification and sensitivity by environment group")
    b.p("The classes in {ref:tab_data_inventory} map to the customer's own classification scheme. Restricted means personal or "
        "otherwise sensitive data; Confidential means identifiers and business context without personal content; Internal "
        "means technical data with no business content; Secret means credentials. The data security officer confirms the "
        "mapping before M2 (OD-15).")
    b.p("The class of a store follows the data in the database it was built from, not the environment's name.")
    b.table(["Group", "Database content", "Kafka and OpenSearch then hold", "Controls required"], [
        ["PROD", "Production data", "Production personal data", "All controls in this section"],
        ["NP2 (PERF, PREPROD)", "Masked clone, or unmasked production clone if the customer keeps PREPROD unmasked (OD-15)", "Masked data, or production personal data", "If either NP2 environment holds unmasked data, cc-np2 and os-np2 are production-class stores and need the PROD controls"],
        ["NP1 (DEV, SIT, UAT)", "Masked clone (OD-07)", "Masked data only, if masking ran before the index build (Section 11.5)", "Encryption, access and retention controls; production-only controls may be relaxed by the data security officer"],
    ], caption="Data class by environment group", widths=[2.6, 4.6, 4, 5.4], size=8.5, label="data_groups")
    b.callout("important", ["NP2 is shared by PERF and PREPROD. If PREPROD runs on an unmasked production clone, the shared "
              "Confluent cluster and OpenSearch service hold production personal data, and everyone with administrator access "
              "to them can reach it, whatever the per-environment ACLs say. Either mask PREPROD as well, or classify and "
              "protect the whole of NP2 as production, including the self-managed key decision (OD-14), which cannot be "
              "changed after the cluster is created [R74].",
              "Masking that runs after the index build leaves unmasked data in the indexes and in any Kafka message produced "
              "in between (Section 11.5). The order clone, mask, upgrade, first start is a data protection control, not only a "
              "test convenience."])

    b.h2("Keeping personal data out of Kafka and search")
    b.p("The safest copy is the one that is never made. Four Pega settings decide how much case data leaves the database.")
    b.table(["Control", "Setting", "Recommendation", "Check"], [
        ["Queue processor payload", "\"Queue current snapshot of page\" on Queue-For-Processing and Run in Background [R64]", "Leave it off for case pages, so only the key travels. Allow it only where a queue processor must see the page as it was, with the data owner's approval", "Inventory of queue processors and shapes with the option on (DT-01)"],
        ["Indexed properties", "Relevant Records and Custom Search Properties per class [R67, R68]", "Index only properties that searches and reports use. Mark as available for full-text search only those users must find by free text", "Approved list per class; DT-03 compares the index mapping with it"],
        ["Index everything", "DSS `indexer/srs/indexAllFieldsForFTS` [R68]", "Leave unset in every environment. It makes every indexable Work and Data property searchable by free text", "DSS export at time point A and after each deployment"],
        ["Property encryption", "PropertyEncrypt access control policy on Work-, Data- and Index- classes [R71]", "Use for Restricted text properties that must be stored. The value is encrypted in the database, clipboard, logs and search indexes [R71]. The Pega keystore can hold its master key in Azure Key Vault [R72]", "DT-04 shows ciphertext in the index and records the effect on search"],
    ], caption="Controls that limit the data copied to Kafka and OpenSearch", widths=[2.8, 4.2, 5.6, 4], size=8, label="data_min")
    b.callout("note", ["Class-level BLOB encryption does not encrypt properties exposed as columns [R71], and Pega does not say "
              "whether a page snapshot in a queue processor message, or a broken item, is encrypted when its class uses BLOB "
              "encryption or a PropertyEncrypt policy (GQ-09). Until Pega Support answers, treat D-03 and D-04 as Restricted "
              "plaintext.",
              "TextEncrypted is deprecated in favour of PropertyEncrypt policies [R71]. A clone from 8.8 may still use it; "
              "list such properties during the clean-up (Section 11.3)."])

    b.h2("Encryption in transit")
    b.p("Every hop that carries Pega data is encrypted and authenticated. {ref:tab_transit} lists them with the check that "
        "proves each one.")
    b.table(["Hop", "Protocol and port", "Server identity", "Client authentication", "Check"], [
        ["Pega to Confluent", "SASL_SSL on 9092 over Private Link (Section 6.4). Confluent Cloud accepts only TLS; it prefers TLS 1.3 and falls back to TLS 1.2 [R75]", "Confluent certificate from a public CA", "API key over SASL/PLAIN inside TLS", "DT-02: negotiated version and chain; plaintext refused"],
        ["Pega to SRS", "HTTPS on 8443 inside the cluster (Section 7.7)", "SRS certificate from the customer private CA", "Okta access token (JWT)", "DT-02; S-5"],
        ["SRS to OpenSearch", "HTTPS on 443 over the provider's private endpoint", "Provider or customer CA", "SRS user, basic authentication", "DT-02; plain HTTP refused"],
        ["OpenSearch node to node", "OpenSearch transport layer; TLS is mandatory there and optional on the REST layer [R76]", "Node certificates", "Node certificates", "Provider statement (mandatory criterion in Section 7.3)"],
        ["Pega and SRS to Okta", "HTTPS on 443", "Okta certificate from a public CA", "Signed client assertion (`private_key_jwt`)", "O-1"],
        ["Pega to database", "JDBC over TLS (Section 4.2)", "Database server certificate", "Database user", "DBA check"],
        ["Node logs to Log Analytics", "Azure Monitor agent over HTTPS [R60]", "Microsoft certificate", "Managed identity", "Container insights data arrives"],
    ], caption="Encryption in transit per hop", widths=[2.6, 5, 2.8, 2.8, 3.4], size=8, label="transit")
    b.bullets([
        "Dedicated Confluent clusters created before 30 April 2026 must have TLS 1.3 enabled explicitly; Confluent advises keeping TLS 1.2 enabled until every client has been seen working on TLS 1.3 [R75]. Record the negotiated version from a Pega pod in DT-02 before any change to `ssl.enabled.protocols`.",
        "OpenSearch itself allows plain HTTP on the REST layer [R76]. The provider must enforce HTTPS only; this is a mandatory criterion in {ref:tab_os_score}.",
        "No TLS-inspecting proxy sits on these paths (Section 8.4). Inspection would also put decrypted case data on the proxy.",
    ])

    b.h2("Encryption at rest")
    b.p("{ref:tab_at_rest} lists every store that holds data from {ref:tab_data_inventory}. Three of the key choices can only be "
        "made when the resource is created, so they are decisions for M2, not for go-live.")
    b.table(["Store", "Default protection", "Customer-managed key option", "When it must be decided", "Recommendation"], [
        ["Confluent cluster", "Every cluster is encrypted at rest by the cloud provider's encryption services [R73]", "Self-managed key in Azure Key Vault on Enterprise and Dedicated: RSA or RSA-HSM key in the same region, purge protection, Azure RBAC [R74]", "At cluster creation; the mode cannot be changed later [R74]", "Decide per group under OD-14. Default encryption is acceptable for NP1; follow the customer's key policy for cc-prd and for cc-np2 if it holds production data"],
        ["OpenSearch service", "Provider-specific", "Provider-specific", "Usually at service creation", "Encryption at rest for data and snapshots is a mandatory provider criterion; a customer key is scored ({ref:tab_os_score})"],
        ["AKS node disks (container logs, GC logs, heap dumps)", "OS and data disks use server-side encryption with platform keys. Temp disks, ephemeral OS disks and disk caches are encrypted only with encryption at host [R78]", "Disk encryption set with a customer key; for the OS disk only at cluster creation [R79]", "Encryption at host at node pool creation [R78]; OS disk key at cluster creation [R79]", "Encryption at host on every Pega and SRS node pool in every environment (OD-18)"],
        ["Pega database", "Database platform encryption per the DBA standard", "Per database service", "At database creation", "Unchanged by this design; PropertyEncrypt adds field-level protection ({ref:tab_data_min})"],
        ["Key Vault", "Protected by the vault service", "Not applicable", "Not applicable", "Unchanged (Section 8)"],
        ["Log Analytics", "Microsoft-managed", "Per the monitoring standard", "At workspace creation", "Production logs only in the production workspace (Section 19.2)"],
    ], caption="Encryption at rest per store", widths=[2.6, 3.8, 3.8, 2.8, 3.6], size=7.5, label="at_rest")
    b.callout("caution", ["For Enterprise clusters on Azure, Confluent requires the Key Vault firewall to allow public access "
              "from all networks so Confluent can reach the key; only Dedicated clusters can use the \"Allow trusted Microsoft "
              "services\" exception [R74]. Step SI-1 creates every Pega vault with public access disabled.",
              "If a self-managed key is required on an Enterprise cluster, keep the key in a separate vault, "
              "`kv-cc-key-<group>`, that holds only that key and grants Confluent's identity the Key Vault Crypto Service "
              "Encryption User role and nothing else [R74]. Otherwise choose Dedicated for that group. Either way, take the "
              "decision before the cluster exists, because the encryption mode is fixed at creation [R74]."])
    b.callout("caution", "AKS uses ephemeral OS disks by default when the VM size allows it [R79]. Container logs and anything "
              "a pod writes to its own file system, including the GC log and heap dumps, then sit on storage that server-side "
              "encryption does not cover. Encryption at host can be set only when a node pool is created [R78], so a pool "
              "created without it has to be replaced. Check that the region and VM sizes support it before the first pool "
              "is created.")
    b.code("""# Node pool with encryption at host and three zones (set at creation only [R78, R59])
az aks nodepool add --resource-group <rg> --cluster-name <aks> --name pegaweb \\
  --node-vm-size <size> --zones 1 2 3 --enable-encryption-at-host
# Evidence for DT-11
az aks nodepool list --resource-group <rg> --cluster-name <aks> -o table \\
  --query "[].{pool:name, eah:enableEncryptionAtHost, zones:availabilityZones}\"""",
           title="Creating and checking node pools with encryption at host")

    b.h2("Personal data in operations: logs, dumps, broken items and support")
    b.p("Most leaks in practice come from operational copies, not from the main data path. {ref:tab_ops_data} sets the rules "
        "for each.")
    b.table(["Copy", "Risk", "Rule"], [
        ["Heap dumps (D-12)", "Contain every value in memory, including decrypted PropertyEncrypt values, tokens and the JAAS value", "Create only for an incident. Copy to an encrypted, access-controlled storage account in the same tenancy, record it in the incident, delete it when the incident closes. A production dump leaves the tenancy only with the data owner's written approval"],
        ["Broken items (D-04)", "Hold the message payload in the database and show its XML in Admin Studio", "Grant `pzQueueProcessorObserver` and `pzQueueProcessorAdministrator` [R64] to operations roles only. Resolve or delete broken items within the agreed period (OD-17)"],
        ["Pega logs (D-11)", "Exceptions and debug loggers can write page content", "No DEBUG on stream, queue processor or search loggers in PROD except for a time-boxed incident with approval. The weekly log scan (Section 19.2) also looks for the customer's personal data patterns"],
        ["OpenSearch slow logs (D-08)", "Record the query, which may include search terms [R58]", "Classify as Restricted; same retention and access as production logs"],
        ["OpenSearch audit log (D-14)", "Can copy request bodies into the audit index", "Turn on audit logging for authentication failures and for access by any user other than the SRS user, without request bodies [R77]"],
        ["Kafka tooling", "A console consumer on a PROD topic copies messages to a laptop or jump host", "No human consumer on PROD Pega topics. Tests in PROD use a dedicated test topic. In NP1 tools read masked data only"],
        ["OpenSearch administrator access", "Bypasses Pega's access control on search results", "Break-glass group only; every use logged and reviewed. No dashboards user with read rights on `pega26-prd*`"],
        ["Pega Support cases", "Logs, dumps and PDC data attached to a case leave the tenancy", "Reproduce in a masked environment where possible; send production artefacts only with the data owner's approval"],
    ], caption="Rules for operational copies of data", widths=[3.2, 5.2, 8.2], size=8, label="ops_data")

    b.h2("Residency, retention and erasure")
    b.p("All stores for an environment are in the AKS region unless the customer approves otherwise. {ref:tab_residency} "
        "lists where each copy lives and how long it stays.")
    b.table(["Copy", "Location", "Kept for", "Removed by"], [
        ["Kafka messages (D-02, D-03, D-05)", "Confluent cluster in the AKS region; Cluster Linking would copy topics to another cluster [R35]", "`retention.ms`, default 7 days, with `cleanup.policy` delete [R33] (OD-16)", "Expiry only. Kafka deletes whole log segments, so a record can stay a little longer than `retention.ms`. Deleting the topic removes everything (refresh and retirement, Sections 20.3 and 20.4)"],
        ["Delayed and broken items (D-04)", "Pega database", "Until processed, requeued or deleted", "Admin Studio, after the cause is fixed (OD-17)"],
        ["Index documents (D-06)", "OpenSearch provider region", "As long as the record is indexed", "Pega's indexing when the record changes or is deleted (GQ-11, DT-06); class reindex; index deletion at refresh and retirement"],
        ["Snapshots (D-06)", "Provider snapshot repository", "Snapshot retention (OD-13)", "Snapshot expiry. Erased records stay in snapshots until they expire"],
        ["Logs (D-11, D-08)", "Log Analytics workspace region", "Workspace retention (Section 19.2)", "Expiry"],
        ["PDC data (D-13)", "Pega Diagnostic Center", "Per Pega's terms", "Per Pega's terms; review before PROD connects"],
        ["Tokens (D-09)", "Memory only", "Token lifetime", "Expiry"],
    ], caption="Residency and retention per copy", widths=[3.2, 4.4, 4, 5], size=8, label="residency")
    b.bullets([
        "**Kafka retention (OD-16).** A queue message is needed only until it is processed, so a long retention mostly keeps old personal data. A short retention loses unprocessed messages after an outage longer than the retention. Keep the Confluent default of 7 days unless the customer's policy needs less, and never set it below the longest consumer outage the business must survive. The consumer lag alert (Section 19.5) must fire well before the oldest unprocessed message reaches the retention limit. Read the actual `retention.ms` of the Pega topics after the first start (DT-05), because Pega creates the topics itself.",
        "**Erasure requests.** Delete or purge the record in Pega through the application's normal process. Then confirm the index documents are gone (DT-06), delete any delayed or broken item for the record, and record the date by which Kafka retention and snapshot retention will have removed the remaining copies. Kafka cannot delete a single message from a topic with the delete policy.",
    ])

    b.h2("What happens to data when a transfer fails")
    b.p("Pega keeps the database as the system of record and retries transfers to Kafka and SRS, so most failures delay data "
        "rather than lose it. The cases where data can be lost or left stale are narrow, and each has a control. "
        "{ref:fig_data_failure} shows the two paths and {ref:tab_data_fail} lists the failures.")
    b.figure(GEN + "fig_data_failure.png", "Failure handling for queue processor messages and search index updates", OWN, width_cm=13, label="data_failure")
    b.table(["ID", "Failure", "What Pega does", "Data at risk", "Detection", "Remediation"], [
        ["DF-01", "Kafka unreachable when a message is queued", "Holds the message in the database; a job scheduler queues it to Kafka when the service returns [R66]", "None if the database commit succeeded; processing is delayed", "Stream landing page; delayed item count (Section 19.5)", "Restore Kafka; watch the delayed items drain (FS-01)"],
        ["DF-02", "Message over the topic size limit", "Producer error for that item", "The item is not queued", "RecordTooLargeException (FS-06)", "Topic at 5,000,000 bytes; avoid page snapshots of large pages"],
        ["DF-03", "Processing activity fails", "Retries through delayed items, then moves the item to the broken queue after MaxAttempts [R64, R66]", "None; the item and payload are kept", "Broken item count alert", "Fix the cause; requeue or delete in Admin Studio [R64]"],
        ["DF-04", "Consumer pod stops part way through a batch", "Another consumer takes the partition", "An item can be processed twice", "Duplicate outcomes in application checks", "Write queue processor activities so a repeat of the same item has no extra effect (DT-07)"],
        ["DF-05", "Consumer lag exceeds topic retention", "Kafka deletes the oldest segments [R33]", "Unprocessed messages are lost", "Lag alert before the limit", "Never let lag approach retention; recover lost work from the database by the application's reconciliation"],
        ["DF-06", "SRS, OpenSearch or Okta unavailable during indexing", "The indexer retries; then a broken item with a CONNECTION or STORAGE error [R69]", "None in the database; search is stale until requeued", "Indexer broken item count; search landing page", "Restore the service; requeue broken items; reconcile counts (FS-10, FS-11)"],
        ["DF-07", "One bad item in a bulk request", "By default the whole bulk of 100 items fails [R70]", "Up to 100 items unindexed", "Broken items with the same error", "Fix the item; lower `indexer/engine/maxBulkSize` while isolating it [R70]"],
        ["DF-08", "Value that does not match its property type", "With `indexer/srs/failOnUnrecognisedValue` false, the field is skipped and the item indexed [R69]", "That field is silently missing from the index", "UNRECOGNISED_VALUE errors; field-level checks in DT-03", "Fix the data; reindex the class; record every use of the setting"],
        ["DF-09", "OpenSearch at the flood-stage watermark", "Indexes become read-only and indexing stops (FS-17)", "Search stale", "Disk alert (Section 19.5)", "Add storage; clear the block; requeue"],
        ["DF-10", "Index and database diverge after an incident", "No automatic reconciliation", "Search shows missing, stale or deleted data", "Count comparison per class (Section 7.8)", "Reindex the affected classes"],
        ["DF-11", "Masking runs after the index build", "None; the index keeps what it was given", "Unmasked data in a non-production index", "Masking report date against the build start", "Delete the environment's indexes and rebuild (Section 11.5)"],
    ], caption="Data transfer failures and their handling", widths=[1.2, 2.8, 3.6, 2.8, 2.8, 3.4], size=7.5, label="data_fail")
    b.callout("important", "A Kafka message is delivered at least once. Pega does not document exactly-once processing for "
              "queue processors, so a restart or rebalance can repeat an item (DF-04). Activities that send emails, call "
              "external systems or create records should check whether the work is already done. Test this in DT-07 by "
              "deleting a batch pod during a load test.")

    b.h2("Data tests")
    b.p("Run DT-01 to DT-12 in DEV on masked data, repeat DT-02, DT-05, DT-06 and DT-11 in PREPROD, and collect DT-02 and "
        "DT-11 evidence in PROD before go-live.")
    b.table(["ID", "Test", "Method", "Pass criteria"], [
        ["DT-01", "Queue payload inventory", "List queue processors, Queue-For-Processing steps and Run in Background shapes with the snapshot option; in DEV, read one message per such queue from a test consumer", "Every snapshot use approved by the data owner; payloads match {ref:tab_data_inventory}"],
        ["DT-02", "TLS on every hop", "DP-1 to DP-3; attempt plaintext on each port", "TLS 1.2 or 1.3 with a valid chain; plaintext refused"],
        ["DT-03", "Index content", "Read the mapping of each main index and sample documents as an administrator in DEV (DP-4)", "Only properties on the approved list; no excluded field present"],
        ["DT-04", "Property encryption", "Save a test case with a PropertyEncrypt property; read its index document", "Ciphertext in the index; effect on search recorded"],
        ["DT-05", "Kafka retention", "DP-5 for every Pega topic after the first start", "`retention.ms` equals the OD-16 value on every topic"],
        ["DT-06", "Erasure from search", "Delete and purge a test case; query its key in the index after the indexer has run", "No document for the key; result recorded against GQ-11"],
        ["DT-07", "Repeat delivery", "Delete a batch pod during PT-04; compare outcomes with the items queued", "No duplicate side effects"],
        ["DT-08", "Kafka outage and recovery", "FS-01 with counts of items queued, delayed and processed", "Every item processed once the service returns"],
        ["DT-09", "Heap dump handling", "Take a test dump in DEV with `jcmd`; follow {ref:tab_ops_data}", "Location recorded; copy and deletion procedure works"],
        ["DT-10", "Personal data in logs", "Run the log scan queries over a test run with known test values", "No test value found outside approved fields"],
        ["DT-11", "Encryption at rest evidence", "Confluent cluster encryption mode; provider statement; DP-6 node pool list; database setting", "Every store in {ref:tab_at_rest} matches the decision"],
        ["DT-12", "Residency", "Region of every endpoint; Cluster Linking and snapshot destinations", "All in the approved region"],
    ], caption="Data tests", widths=[1.2, 3, 7.2, 5.2], size=8, label="data_tests")
    b.code("""# Run DP-1 and DP-2 from a tools pod in pega-<code>, DP-3 from one in srs-<code>
# DP-1 Confluent: negotiated TLS version and certificate chain
openssl s_client -connect <bootstrap-host>:9092 -servername <bootstrap-host> -brief </dev/null

# DP-2 SRS: TLS on 8443 works; plain HTTP on the same port fails
SRS=srs-<code>.srs-<code>.svc.cluster.local:8443
openssl s_client -connect $SRS -CAfile srs-ca.crt -brief </dev/null
curl -s -o /dev/null -w "%{http_code}\\n" "http://$SRS/health"

# DP-3 OpenSearch: negotiated TLS version; plain HTTP refused
openssl s_client -connect <search-host>:443 -servername <search-host> -brief </dev/null
curl -s -o /dev/null -w "%{http_code}\\n" "http://<search-host>/"

# DP-4 Index mapping (DEV only; administrator through the break-glass process)
curl -s -u "$OS_ADMIN:$OS_ADMIN_PASSWORD" "https://<search-host>/pega26-<code>*/_mapping?pretty"

# DP-5 retention.ms of every Pega topic
confluent kafka topic list --cluster <lkc-id> -o json \\
  | jq -r '.[].name | select(startswith("pega-<code>-"))' | while read -r t; do
    echo "$t"; confluent kafka topic describe "$t" --cluster <lkc-id> | grep retention.ms; done

# DP-6 Node pools: encryption at host
az aks nodepool list -g <rg> --cluster-name <aks> \\
  --query "[].{pool:name, eah:enableEncryptionAtHost}" -o table""",
           title="Data protection commands DP-1 to DP-6 (check flags with --help)")

    b.h2("Decisions, questions and risks raised by this section")
    b.p("These items are also in the main registers: decisions in Section 21.2, Pega Support questions in Section 11.1 and "
        "risks in Section 21.1.")
    b.table(["ID", "Item", "Recommended answer or mitigation"], [
        ["OD-14", "Confluent encryption keys per group", "Provider-managed for NP1; customer key for cc-prd and for cc-np2 if it holds production data, if the key policy requires it; Dedicated or a key-only vault for Enterprise"],
        ["OD-15", "Data class of PERF and PREPROD", "Mask both, so NP2 holds no production personal data"],
        ["OD-16", "Retention of Pega topics", "7 days (Confluent default) unless policy needs less; never below the longest outage to survive"],
        ["OD-17", "Retention of broken items and the approved list of indexed properties", "Broken items resolved or deleted within 30 days; indexed property list signed by the data owner"],
        ["OD-18", "Encryption at host and disk keys for AKS node pools", "Encryption at host on all pools; customer key per the key policy, decided before the cluster is created"],
        ["GQ-09", "Are page snapshots in queue messages, delayed items and broken items encrypted when the class uses BLOB encryption or PropertyEncrypt?", "Treat as plaintext until answered"],
        ["GQ-10", "What does cluster messaging over Kafka carry in 26.1.1, and can it include case data?", "Treat as Confidential until answered"],
        ["GQ-11", "In SRS mode, are index documents removed when a record is deleted, purged or archived?", "DT-06 records the behaviour"],
        ["RK-17", "Personal data copied to Kafka through page snapshots", "DT-01; snapshot only with approval"],
        ["RK-18", "Personal data reachable by OpenSearch or Confluent administrators", "Index minimisation; break-glass access; audit logging; OD-15"],
        ["RK-19", "Personal data leaked through logs, heap dumps or support cases", "{ref:tab_ops_data}; DT-09, DT-10"],
        ["RK-20", "Key decision taken after the cluster or node pool exists, forcing a rebuild", "OD-14 and OD-18 by M2"],
        ["RK-21", "Unprocessed messages lost because lag exceeded retention", "OD-16; lag alert; DT-08"],
    ], caption="Data decisions, Pega Support questions and risks", widths=[1.4, 7, 8.2], size=8, label="data_items")
