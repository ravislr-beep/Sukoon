"""Sections 5 to 7: shared service model, Confluent Cloud, OpenSearch with SRS and Okta."""
from content_a import GEN, PUB, OWN
import envs as E


def s5_shared(b):
    b.h1("Shared and dedicated service model")
    b.p("Pega allows one Kafka cluster and one search service to serve more than one Pega deployment. Kafka isolation comes "
        "from the stream name prefix and prefixed ACLs [R11]. Search isolation comes from the customerDeploymentId, which "
        "SRS uses as the index prefix [R14, R23]. This section uses those features to cut the number of service sets from six "
        "to three, and states the controls that keep each environment's data apart.")
    b.h2("Grouping options")
    b.p("Four groupings were assessed. {ref:tab_grouping} compares them. Option B is recommended.")
    b.table(["Option", "Service sets", "Strengths", "Weaknesses"], [
        ["A. Dedicated per environment", "6 Kafka clusters, 6 OpenSearch services", "No shared blast radius; simplest isolation", "Highest cost; six sets to patch, monitor and rotate"],
        ["B. Two shared groups plus PROD (recommended)", "NP1: DEV, SIT, UAT. NP2: PERF, PREPROD. PROD dedicated. 3 sets in total", "Load tests and rehearsals run on production-like services without touching functional testing; PREPROD matches PROD", "PERF and PREPROD runs must be scheduled so they do not overlap"],
        ["C. One shared non-production set plus PROD", "2 sets", "Lowest cost", "A PERF load test or PREPROD rehearsal affects DEV, SIT and UAT; non-production services cannot match PROD type without paying PROD price for all"],
        ["D. PREPROD alone, others shared", "DEV, SIT, UAT, PERF shared; PREPROD; PROD. 3 sets", "PREPROD fully separate", "PERF load tests affect functional testing; same number of sets as B with less benefit"],
    ], caption="Non-production grouping options", widths=[3.4, 4, 4.6, 4.6], size=8.5, label="grouping")
    b.figure(GEN + "fig_decision_env_grouping.png", "Decision: placing a non-production environment on shared services", OWN, width_cm=11.5)
    b.h2("Recommended model")
    b.p("{ref:fig_shared} shows the two non-production groups and {ref:fig_prod} shows production. Each environment has its "
        "own namespace, topic prefix, service account, customerDeploymentId, SRS deployment, OpenSearch user, Okta client and "
        "Key Vault. Only the Kafka cluster and the OpenSearch service are shared within a group.")
    b.figure(GEN + "fig_shared_topology.png", "Shared non-production topology and per-environment boundaries", OWN, width_cm=15.5, label="shared")
    b.figure(GEN + "fig_prod_topology.png", "Production topology with dedicated services", OWN, width_cm=15.5, label="prod")
    b.h2("Isolation controls")
    b.p("Isolation is enforced at every layer, so a single mistake does not expose another environment. {ref:tab_isolation} "
        "lists the control at each layer and the test that proves it.")
    b.table(["Layer", "Control", "What it prevents", "Proof (Section 15.3)"], [
        ["Kafka topics", "Prefix `pega-<code>-` per environment through `stream.streamNamePattern`; TOPIC ACL ALL PREFIXED on that prefix only [R11, R23]", "Reading, writing or deleting another environment's topics", "IT-01, IT-02"],
        ["Kafka consumer groups", "GROUP ACL ALL PREFIXED on the same prefix [R11]", "Joining or resetting another environment's consumer groups", "IT-03"],
        ["Kafka credentials", "One service account per environment; API keys in that environment's Key Vault only [R36]", "Credential reuse across environments", "IT-04"],
        ["Kafka capacity", "Client quota per service account on Enterprise or Dedicated clusters [R36]", "One environment's load starving the others", "PT-03"],
        ["Search indexes", "customerDeploymentId `pega26-<code>`, used as the index prefix [R23]", "Index name collisions", "IT-05"],
        ["Search credentials", "One SRS deployment and one OpenSearch user per environment, with a role limited to index pattern `pega26-<code>*` if SRS accepts it (Section 7.5) [R40, R41]", "One environment's SRS reading or deleting another's indexes", "IT-06"],
        ["Search tokens", "Okta client per environment; SRS checks that `guid` equals its own customerDeploymentId [R23]", "A token for one environment being accepted by another environment's SRS", "IT-07"],
        ["Secrets", "Key Vault per environment; External Secrets Operator identity per namespace [R48]", "Pods reading another environment's secrets", "IT-08"],
        ["Network", "Firewall allow-list per environment; Kubernetes network policies deny by default", "A cloned environment reaching production Kafka, production OpenSearch or production integrations", "IT-09, IT-10"],
        ["Cloned data", "Application Kafka data sets and other endpoints repointed or disabled before the batch tier starts (Section 11.4)", "Test environments consuming production topics or calling production systems", "IT-10, FS-27"],
    ], caption="Isolation controls by layer", widths=[2.6, 6.4, 4.4, 3.2], size=8.5, label="isolation")
    b.p("{ref:fig_layers} shows the same controls as layers. A request from one environment has to pass every layer to reach "
        "another environment's data, so a single misconfiguration does not expose it.")
    b.figure(GEN + "fig_isolation_layers.png", "Isolation layers between environments on shared services", OWN, width_cm=14, label="layers")
    b.callout("caution", ["Wildcard ACLs are forbidden on a shared cluster. Pega's ACL list includes TRANSACTIONAL_ID `*` "
              "[R11], which every environment needs. That ACL does not give access to topics or groups, but it means "
              "transactional IDs are not separated by environment. Record this as an accepted residual risk (RK-07).",
              "Never grant TOPIC or GROUP with a literal `*` or with the bare prefix `pega-`, which would match every environment."])
    b.h2("Noisy neighbours and quotas")
    b.p("Confluent supports client quotas on Enterprise, Freight and Dedicated clusters. Quotas apply to a service account or "
        "an identity pool, not to an API key, and the Metrics API labels throughput by principal [R36]. One service account "
        "per environment therefore gives both a quota boundary and per-environment metrics.")
    b.bullets([
        "Set a produce and a consume quota per service account in NP1 and NP2, sized from the measured peak of that environment plus headroom (OD-09).",
        "Leave PROD without quotas unless another workload is added to its cluster.",
        "In NP2, PERF load tests and PREPROD rehearsals are booked in a shared calendar. A run that overlaps the other environment's run needs both test leads' approval.",
        "If a load test in one environment affects another, stop the test, check the Metrics API by principal, lower that service account's quota and rerun (FS-22).",
    ])
    b.p("OpenSearch has no equivalent quota per user. In the shared search services, limit the effect of one environment on "
        "the others by running full index builds outside the other environments' test hours, and by sizing the data nodes "
        "for the largest concurrent build (Section 7.4).")
    b.h2("Cost comparison model")
    b.p("Prices change and depend on the customer's agreements, so this document gives no figures. {ref:tab_cost_inputs} "
        "lists the inputs the customer supplies, and {ref:tab_cost_model} shows how each option is costed from them.")
    b.table(["Input", "Where it comes from", "Notes"], [
        ["Confluent cluster base price per type", "Confluent price list or contract", "Enterprise and Dedicated differ in pricing unit (eCKU or CKU) [R31]"],
        ["Capacity units per cluster", "Measured partitions and throughput (Section 6.7)", "Shared clusters add the needs of each environment"],
        ["Private Link and data transfer", "Confluent and Azure price lists", "One set of private endpoints per cluster"],
        ["OpenSearch nodes per service", "Sizing in Section 7.4", "Cluster-manager and data nodes"],
        ["OpenSearch storage and snapshots", "Provider price list", "Measured searchable data volume"],
        ["Operations effort per service set", "Customer operating model", "Patching, monitoring, on-call, key rotation"],
        ["Support plans", "Confluent and provider contracts", "Production support level for PROD and NP2"],
    ], caption="Cost model inputs supplied by the customer", widths=[4.4, 5, 7.2], size=9, label="cost_inputs")
    b.table(["Cost line", "Option A", "Option B (recommended)", "Option C"], [
        ["Kafka clusters", "6 x (base + units)", "NP1 + NP2 + PROD: 3 x (base + units)", "2 x (base + units)"],
        ["Private Link sets", "6", "3", "2"],
        ["OpenSearch services", "6 x (nodes + storage)", "3 x (nodes + storage)", "2 x (nodes + storage)"],
        ["SRS deployments", "6 (inside AKS)", "6 (inside AKS)", "6 (inside AKS)"],
        ["Okta authorization servers", "Up to 6", "2 (PROD and shared non-production)", "2"],
        ["Operations effort", "6 service sets", "3 service sets", "2 service sets"],
        ["Risk cost", "Lowest", "Shared blast radius within NP1 and NP2; scheduling in NP2", "Load tests affect all non-production; no production-like test services"],
    ], caption="Cost model by option (multiply each line by the customer's unit prices)", widths=[3.6, 3.6, 5.2, 4.2], size=8.5, label="cost_model")
    b.p("Option B removes three Kafka clusters and three OpenSearch services compared with Option A. The saving is the base "
        "price of those services plus their private endpoints and operations effort, less any extra capacity units the "
        "shared clusters need. Option C saves one more set but removes the production-like test services, which raises the "
        "chance of a production problem that rehearsals did not show.")
    b.h2("Production")
    b.p("Production always has its own Confluent cluster, its own OpenSearch service, its own Okta authorization server and "
        "its own Key Vault. Production credentials, endpoints and DNS zones are not linked to any non-production network.")


def s6_kafka(b):
    b.h1("Confluent Cloud design and configuration")
    b.h2("What Pega uses Kafka for")
    b.p("Pega uses Kafka in two ways. The stream service carries every queue processor and job scheduler, so Pega is not fully "
        "functional without it [R11]. This is what the Helm `stream` section configures. Separately, a Kafka data set is an "
        "application feature that reads from or writes to the customer's own Kafka topics. Pega requires that Kafka data sets "
        "use a different Kafka service from the stream service [R11]. Section 12.3 covers data sets.")
    b.figure(PUB + "pega_docs_kafka-use-cases.jpg", "The two Kafka use cases in Pega Platform",
             "Source: Pega Documentation, \"External Kafka in your deployment\" [R11]. © Pegasystems Inc. Reproduced with attribution.",
             width_cm=15.5)
    b.callout("important", "From '25, Pega uses its streaming function and the external Kafka service for the cluster "
              "messaging that Hazelcast used to carry, and Pega asks clients to review the Kafka configuration before the "
              "change [R7]. A Kafka outage on 26.1.1 therefore affects more than queue processing. Treat the Kafka service as "
              "a tier-1 dependency and test its loss explicitly (FS-01, FS-03).")
    b.h2("Pega requirements mapped to Confluent Cloud")
    b.p("Confluent Cloud is a managed service, so some broker settings Pega lists cannot be changed by the customer. "
        "{ref:tab_cc_map} shows each requirement, what Confluent Cloud allows, and what the runbook does.")
    b.table(["Pega requirement", "Confluent Cloud position", "Action"], [
        ["Kafka client 4.0.0 in '26, compatible with 3.9.2 [R3]", "Fully managed Kafka", "Produce, consume and transactional checks from a Pega pod in every environment (Section 15.4)"],
        ["Confluent 5.4.x or later [R11]", "Current release line", "None beyond the checks above"],
        ["message.max.bytes 5000000 [R11]", "Topic max.message.bytes default 2,097,164; editable up to 20,971,520 on Enterprise and Dedicated [R33]", "After each start, set max.message.bytes to 5,000,000 on every Pega topic (command K-6)"],
        ["replica.fetch.max.bytes and replica.fetch.response.max.bytes 5000100 [R11]", "Not in the list of editable cluster settings [R34]", "Ask Confluent support to confirm in writing (RC-03)"],
        ["unclean.leader.election.enable false [R11]", "Not customer-editable [R34]", "Ask Confluent support to confirm in writing (RC-03)"],
        ["auto.create.topics.enable false [R11]", "Editable on Dedicated; default false [R34]", "Keep false. Pega creates topics through its admin client, which needs CREATE in the topic ACL"],
        ["Generic Kafka security only [R11]", "SASL_SSL with API keys (PLAIN) is generic Kafka", "Use SASL_SSL with PLAIN (Section 6.5)"],
        ["ACLs for TOPIC, GROUP, TRANSACTIONAL_ID, CLUSTER IDEMPOTENT_WRITE [R11]", "Supported on service accounts", "Create before the first start (Section 6.5)"],
        ["Production sizing supports about 1000 partitions [R11]", "Partition limits per capacity unit are published [R31]", "Measure after the first start (Section 6.7)"],
    ], caption="Pega Kafka requirements mapped to Confluent Cloud", widths=[4.8, 5.4, 6.4], size=8.5, label="cc_map")
    b.h2("Cluster type per group")
    b.p("Confluent offers Basic, Standard, Enterprise, Dedicated and Freight clusters [R31]. Basic and Standard do not offer "
        "private networking, so they cannot hold cloned or masked production data. Freight does not support idempotent "
        "producers or transactions [R31], and Pega's ACL profile needs both [R11]. That leaves Enterprise and Dedicated.")
    b.table(["Dimension (per unit)", "Basic eCKU", "Standard eCKU", "Enterprise eCKU", "Dedicated CKU"], [
        ["Ingress MBps", "5", "25", "60", "60"],
        ["Egress MBps", "15", "75", "180", "180"],
        ["Partitions (before replication)", "30", "250", "3,000", "4,500"],
        ["Client connections", "", "", "18,000", "18,000"],
        ["Connection attempts per second", "", "", "500", "500"],
        ["Requests per second", "", "", "7,500", "15,000"],
        ["Partition creations and deletions per 5 minutes (cluster)", "", "", "500", "5,000"],
        ["Maximum message size", "", "", "20 MB", "20 MB"],
        ["Private networking", "No", "No", "Yes (Private Link)", "Yes (Private Link or VNet peering)"],
        ["Client quotas [R36]", "No", "No", "Yes", "Yes"],
    ], widths=[4.6, 2.6, 2.6, 3.2, 3.6], caption="Confluent Cloud cluster limits relevant to Pega (source [R31]; Basic and Standard rows for connections and requests are not used here)", size=9, label="cc_limits")
    b.callout("important", ["Confluent now enforces the connection and request limits on Enterprise clusters rather than "
              "treating them as guidance: request limits from March 2026 and connection limits from June 2026 [R31]. A client "
              "over a limit is throttled, and the Metrics API reports the throttling per principal with the limit that was hit "
              "[R56].",
              "Pega pods open many Kafka connections: one set per producer, per queue-processor consumer thread and for cluster "
              "messaging. A rolling restart of a large tier, or every environment in a group starting at once after a refresh, "
              "can reach the connection-attempt limit. Measure connections per pod in DEV (Section 16.8), stagger restarts in "
              "shared groups, and alert on throttling (Section 19.5)."])
    b.callout("caution", "Partition creation and deletion are paced at 500 per five minutes per cluster on Enterprise [R31]. "
              "The first start of an environment creates every Pega topic, and a refresh deletes them all. With several hundred "
              "partitions per environment, both can take tens of minutes and slow every other environment on the cluster that "
              "creates topics at the same time. Include this time in the rehearsal measurements and never refresh two "
              "environments in a group at once.")
    b.figure(GEN + "fig_decision_confluent.png", "Decision: Confluent Cloud cluster type", OWN, width_cm=11.5)
    b.table(["Group", "Recommended type", "Reason"], [
        ["NP1 (DEV, SIT, UAT)", "Enterprise with Private Link", "Holds masked production data; quotas available; elastic capacity suits uneven test load"],
        ["NP2 (PERF, PREPROD)", "Same type as PROD", "Load tests and rehearsals must show production behaviour"],
        ["PROD", "Enterprise with Private Link, or Dedicated if measured partitions or throughput exceed Enterprise limits, or VNet peering is required", "Decided after the first PERF measurement (OD-02)"],
    ], caption="Cluster type by group", widths=[3.6, 5.6, 7.4], size=9)
    b.callout("caution", ["Enterprise clusters that use Private Link on Azure are limited to 32 eCKU [R31]. Add up the measured "
              "partitions of every environment in the group before confirming Enterprise.",
              "The 99.99 % uptime SLA applies to Enterprise clusters of at least 2 eCKU, and to Dedicated clusters only when they "
              "are created multi-zone, which needs at least 2 CKU and cannot be changed later [R31]. Set the minimum capacity of "
              "cc-np2 and cc-prd to 2 units. Enterprise scales quickly up to 10 eCKU and more slowly above that, so do not rely on "
              "elastic scaling to absorb a cutover peak above 10 eCKU; raise the minimum before the event."])
    b.h2("Private networking")
    b.p("Azure Private Link gives one-way private access from the customer VNet to Confluent Cloud. Confluent's Azure steps are: "
        "create the Confluent network, add a Private Link access for the customer subscription, create one private endpoint per "
        "zone, create the DNS records, and test [R32]. Each group's cluster needs its own set. The NP1 and NP2 private DNS zones "
        "are linked only to non-production networks, and the PROD zone only to the production network.")
    b.figure(PUB + "confluent_azure_privatelink.png", "Azure Private Link between a customer VNet and Confluent Cloud",
             "Source: Confluent Documentation, \"Use Azure Private Link for Dedicated clusters on Confluent Cloud\" [R32]. © Confluent, Inc. Reproduced with attribution.",
             width_cm=12)
    b.figure(PUB + "confluent_azure_dns_records.png", "DNS records that Confluent lists for Azure Private Link",
             "Source: Confluent Documentation [R32]. © Confluent, Inc. Reproduced with attribution.", width_cm=15.5)
    b.table(["Step", "Action", "Check"], [
        ["N-1", "Create the Confluent network in the AKS region and register the customer subscription for Private Link.", "Network ID and subscription recorded in Appendix A"],
        ["N-2", "Create one private endpoint per zone in the private endpoint subnet, using the service aliases Confluent shows.", "Connection state Approved for each"],
        ["N-3", "Create the private DNS zone for the Confluent network domain with the wildcard and zonal records Confluent shows; link it to the right VNet or resolver.", "Zone export kept as evidence"],
        ["N-4", "From a pod in `pega-<code>`, resolve the bootstrap name and a broker name.", "Both return private IPs (K-1)"],
        ["N-5", "From the same pod, open TLS to the bootstrap name on port 9092.", "Certificate chain shown (K-2)"],
        ["N-6", "Run a metadata request.", "Every broker name resolves privately (K-3)"],
    ], caption="Private Link set-up steps per cluster", widths=[1.3, 9.5, 5.8], size=9)
    b.callout("note", "Confluent states that the Confluent CLI might need internet access to the Confluent control plane even "
              "when the cluster uses Private Link [R32]. Allow that only from the administration jump host, never from Pega pods.")
    b.h2("Service accounts, authentication and ACLs")
    b.p("Pega lists several SASL options [R11], but the Helm `stream.saslMechanism` key accepts PLAIN, SCRAM-SHA-256 and "
        "SCRAM-SHA-512 [R23]. Confluent Cloud API keys use SASL/PLAIN. {ref:fig_kafka_auth} shows the choice.")
    b.figure(GEN + "fig_decision_kafka_auth.png", "Decision: Pega to Kafka authentication", OWN, width_cm=10.5, label="kafka_auth")
    b.p("Create one service account per environment and grant it only the ACLs Pega lists, scoped to that environment's prefix. "
        "{ref:tab_acls} shows the ACLs for one environment; repeat them for each environment on its own cluster.")
    b.table(["Resource type", "Resource name", "Operation", "Pattern", "Why"], [
        ["TOPIC", "`pega-<code>-`", "ALL", "PREFIXED", "Create, write, read and delete Pega topics"],
        ["GROUP", "`pega-<code>-`", "ALL", "PREFIXED", "Consumer groups for queue processors and data flows"],
        ["TRANSACTIONAL_ID", "*", "READ, WRITE", "LITERAL", "Transactional producers"],
        ["CLUSTER", "the cluster", "IDEMPOTENT_WRITE", "LITERAL", "Idempotent producers"],
    ], widths=[3, 3, 2.6, 2.3, 5.7], caption="Kafka ACLs for one environment's service account (source [R11])", size=9, label="acls")
    b.code("""# Confluent CLI. Check flags with: confluent kafka acl create --help
confluent iam service-account create sa-pega-<code> --description "Pega 26.1.1 <ENV>"
confluent kafka acl create --allow --service-account <sa-id> --operations all \\
  --topic "pega-<code>-" --prefix --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> --operations all \\
  --consumer-group "pega-<code>-" --prefix --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> --operations read,write \\
  --transactional-id "*" --cluster <lkc-id>
confluent kafka acl create --allow --service-account <sa-id> \\
  --operations idempotent-write --cluster-scope --cluster <lkc-id>
confluent api-key create --resource <lkc-id> --service-account <sa-id>
confluent kafka acl list --service-account <sa-id> --cluster <lkc-id>""", title="Creating and listing one environment's service account and ACLs")
    b.p("To remove an environment's access, delete its ACLs with `confluent kafka acl delete` using the same flags, delete its "
        "API keys, then delete the service account (Section 20.4).")
    b.h2("Topic design")
    b.table(["Setting", "Value", "Reason"], [
        ["streamNamePattern", "`pega-<code>-{stream.name}`", "Separates environments on a shared cluster. Chart default is `pega-{stream.name}` [R23]."],
        ["replicationFactor", "3", "Pega's recommended value; cannot exceed the number of brokers [R23]."],
        ["Topic creation", "By Pega through its admin client (CREATE in the topic ACL)", "Pega calls broker auto-creation a legacy method [R11]. If policy forbids CREATE, pre-create topics from the rehearsal list (OD-11)."],
        ["max.message.bytes", "5,000,000 on every Pega topic", "Matches Pega's maximum message size [R11]; Confluent default is lower [R33]."],
        ["SystemPulse_SystemPulseTopicName", "6 partitions", "'26 prerequisite; automatic if dynamic topic creation is allowed [R3]."],
        ["Cluster messaging topics after Hazelcast removal", "Covered by the prefixed ACL if Pega applies the pattern to them", "Pega names five topics in the Hazelcast removal prerequisites [R6] but does not say whether the pattern applies. List the topics after the first DEV start and add literal ACLs for any outside the prefix (FS-04)."],
    ], caption="Topic design settings", widths=[3.6, 4.6, 8.4], size=9)
    b.p("When an environment is refreshed from a new clone, keep its prefix and delete its old topics and consumer groups "
        "before the first start (Section 20.3). Keeping the prefix keeps ACLs, quotas and dashboards unchanged. A new prefix "
        "is only needed if old topics cannot be deleted, for example during an investigation; in that case create a new "
        "prefix such as `pega-sit2-` with its own ACLs.")
    b.h2("Partition budget")
    b.p("Since Pega 8.7, each new stream topic is created with 6 partitions by default. The default is set by the DSS "
        "`prconfig/dsm/services/stream/pyTopicPartitionsCount/default` in ruleset Pega-Engine, and applies only to topics "
        "created after the change [R49]. On a queue processor rule, threads beyond the topic's partition count do no work, "
        "because one partition is read by one consumer at a time [R50]. Two rules follow:")
    b.bullets([
        "**Expected partitions per environment** = (number of Pega topics x partitions per topic), counted at replication factor 1. For example, with the default of 6, 150 topics give 900 partitions, close to the 1,000 that Pega's production sizing names [R11].",
        "**Effective consumers per queue processor** = min(partitions, batch pods x threads per node). Adding batch pods beyond the partition count does not speed up a queue processor; raise its partition count first, and only for the queue processors that the load test shows as the bottleneck.",
    ])
    b.callout("caution", "A database cloned from 8.8 may carry a changed `pyTopicPartitionsCount` DSS or per-topic overrides "
              "from tuning on 8.8 (CD-15). Record the value at time point A. If it differs from 6, decide with the performance "
              "lead whether to keep it, because it multiplies the partition count of every topic created at first start.")
    b.p("Partitions drive both Confluent cost and limits. Measure them instead of estimating:")
    b.steps([
        "After the first full start of each environment, count partitions under its prefix (command K-5).",
        "Record the count in {ref:tab_partitions} and add the headroom agreed for new queue processors (30 % is a sound starting point).",
        "Add up the environments in each group and compare with the cluster limit for the chosen type ({ref:tab_cc_limits}).",
        "Repeat after each application release that adds queue processors.",
    ])
    b.table(["Environment", "Group", "Measured partitions", "With 30 % headroom", "Group total", "Cluster limit", "Within limit"],
            E.per_env(lambda n, c, g: [n, g, "<measured>", "<x 1.3>", "<sum for group>", "<from Table>", "<yes or no>"]),
            caption="Partition budget worksheet", widths=[2.4, 1.6, 2.6, 2.6, 2.6, 2.4, 2.4], size=8.5, label="partitions")
    b.h2("Helm stream configuration")
    b.p("The `stream` section connects every tier to Kafka [R12]. Passwords and the JAAS string are left empty in the values "
        "file and supplied by an external secret with the keys STREAM_TRUSTSTORE_PASSWORD, STREAM_KEYSTORE_PASSWORD and "
        "STREAM_JAAS_CONFIG [R23].")
    b.code("""stream:
  enabled: true
  bootstrapServer: "<bootstrap-host>:9092"
  securityProtocol: SASL_SSL
  saslMechanism: PLAIN
  trustStore: ""
  keyStore: ""
  jaasConfig: ""
  streamNamePattern: "pega-<code>-{stream.name}"
  replicationFactor: "3"
  external_secret_name: "pega-stream-secret\"""", title="values-<code>.yaml: stream section")
    b.code("""org.apache.kafka.common.security.plain.PlainLoginModule required
  username="<api-key>" password="<api-secret>";""", title="Value of STREAM_JAAS_CONFIG in Key Vault (stored as one line)")
    b.h2("prpcUtils on 26.1.1")
    b.p("From '25, prpcUtils needs its own connection to Kafka for clustering. Pega documents a `-DNodeSettings` argument in "
        "`custom.jvm.args` of prpcUtils.properties for '25 and '26 [R8]. Pipelines that run prpcUtils against an upgraded "
        "environment must pass that environment's bootstrap server, prefix and JAAS value, generated at run time from Key "
        "Vault and deleted after the run.")
    b.callout("important", "The installer job that runs the upgrade (run U) is built from the same Pega command-line "
              "tooling, but chart 4.13.0 passes it no stream settings: a rendered run U contains no `STREAM_*` values. Whether "
              "the 26.1.1 upgrade of an 8.8 database needs Kafka is therefore an open question for Pega Support (GQ-08). Until it "
              "is answered, allow the installer pod to reach the environment's Confluent endpoint and watch the installer log "
              "for Kafka connection attempts in the first DEV upgrade.")
