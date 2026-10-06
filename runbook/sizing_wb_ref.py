"""Evidence register for the Kafka and OpenSearch sizing workbook.

Every figure here was read from the cited page on 6 October 2026. The quote column holds the
wording the figure comes from so that a reviewer can check it without opening the page.
"""

CHECKED = "6 Oct 2026"

PD = "https://docs.pega.com/bundle/platform/page/platform/"
CC = "https://docs.confluent.io/cloud/current/"
OS = "https://docs.opensearch.org/latest/"
AWS = "https://docs.aws.amazon.com/opensearch-service/latest/developerguide/"
GH = "https://github.com/pegasystems/pega-helm-charts/blob/master/charts/"

# id: (publisher, title, url, what the workbook uses it for)
REFERENCES = {
    "P1": ("Pegasystems", "External Kafka in your deployment (Pega Platform '26)",
           PD + "deployment/externalization-of-services/externalize-kafka-in-your-deployment.html",
           "Kafka sizing (Table 1), 1,000-partition statement, required Kafka settings (Table 2), ACLs, authentication"),
    "P2": ("Pegasystems", "External Search in your deployment (Pega Platform '26)",
           PD + "deployment/externalization-of-services/externalize-search-in-your-deployment.html",
           "Search sizing (Tables 2, 3 and 4), three-node HA rule, supported OpenSearch versions, SRS settings, sharing rule"),
    "P3": ("Pegasystems", "Creating a Queue Processor rule (Pega Platform '26)",
           PD + "background-processing/queue-processor-create-rule.html",
           "Six partitions per queue processor topic; threads beyond the partition count do no work"),
    "P4": ("Pegasystems", "Changing the default number of partitions per topic (Pega Platform '24.1)",
           "https://docs.pega.com/bundle/platform-241/page/platform/deployment/embedded-kafka-cassandra/change-default-partitions-count-stream-nodes.html",
           "Default six partitions per topic from 8.7; DSS prconfig/dsm/services/stream/pyTopicPartitionsCount/default"),
    "P5": ("Pegasystems", "Monitoring an embedded stream service (Pega Platform 8.8)",
           "https://docs.pega.com/bundle/platform-88/page/platform/deployment/embedded-kafka-cassandra/monitor-stream-service.html",
           "Maximum partitions per broker by machine type; 30 % free disk and 70 % CPU action points"),
    "P6": ("Pegasystems", "Completing prerequisites to update to Pega Platform '26",
           PD + "deployment/client-managed-cloud/prereq-pega-platform-26.html",
           "Kafka client library 4.0.0; system pulse topic with 6 partitions"),
    "P7": ("Pegasystems", "Pega Helm chart README, charts/pega (stream section)",
           GH + "pega/README.md",
           "stream.streamNamePattern and replicationFactor (cannot be more than the number of brokers and 3)"),
    "P8": ("Pegasystems", "Removing Hazelcast FAQ (Pega Platform '25)",
           "https://docs.pega.com/bundle/platform-25/page/platform/deployment/externalization-of-services/removing-hazelcast-faq.html",
           "Messaging use cases use the streaming functionality and the external Kafka service instead of Hazelcast"),
    "C1": ("Confluent", "Kafka cluster types in Confluent Cloud",
           CC + "clusters/cluster-types.html",
           "Per-eCKU/CKU limits, maximum units, SLA by type, fast scaling, purchase limits, use cases"),
    "C2": ("Confluent", "Billing dimensions in Confluent Cloud",
           CC + "billing/billing-dimensions.html",
           "Billing on eCKU/CKU-hours, ingress GB, egress GB and storage GB-hours; storage post-replication about 3x"),
    "C3": ("Confluent", "Configuration reference for topics in Confluent Cloud",
           CC + "client-apps/topics/manage.html",
           "max.message.bytes default and maximum by type; retention.ms default; replication factor 3"),
    "C4": ("Confluent", "Protect data at rest using self-managed encryption keys (overview)",
           CC + "security/encrypt/byok/overview.html",
           "Self-managed keys on Azure for Dedicated and Enterprise only; fixed at cluster creation"),
    "O1": ("OpenSearch Project", "Creating a cluster", OS + "tuning-your-cluster/",
           "Three dedicated cluster manager nodes in three zones; data nodes in multiples of three"),
    "O2": ("OpenSearch Project", "Index settings", OS + "install-and-configure/configuring-opensearch/index-settings/",
           "index.number_of_shards default 1; index.number_of_replicas default 1"),
    "O3": ("OpenSearch Project", "Cluster settings", OS + "install-and-configure/configuring-opensearch/cluster-settings/",
           "cluster.max_shards_per_node 1,000; disk watermarks 85 %, 90 %, 95 %"),
    "O4": ("OpenSearch Project", "Installing OpenSearch", OS + "install-and-configure/install-opensearch/index/",
           "Java heap: half of system RAM"),
    "O5": ("OpenSearch Project", "Intro to OpenSearch", OS + "getting-started/intro/",
           "Replica shards are placed on different nodes from their primary shards"),
    "O6": ("OpenSearch Project", "Cluster health API", OS + "api-reference/cluster-api/cluster-health/",
           "A single-node cluster with replica shards shows yellow status because replicas cannot be allocated"),
    "A1": ("Amazon Web Services", "Amazon OpenSearch Service: Calculating storage requirements", AWS + "bp-storage.html",
           "Storage formula with replicas, 10 % indexing overhead, 5 % Linux reserve and 20 % service overhead"),
    "A2": ("Amazon Web Services", "Amazon OpenSearch Service: Choosing the number of shards", AWS + "bp-sharding.html",
           "Shard size 10-30 GiB (search) and 30-50 GiB (write-heavy); at most 25 shards per GiB of heap"),
    "A3": ("Amazon Web Services", "Amazon OpenSearch Service: Choosing instance types and testing", AWS + "bp-instances.html",
           "Minimum three nodes; 2 vCPU and 8 GiB memory per 100 GiB of storage as a starting point for demanding workloads"),
}

# Scalar reference values: (name, group, parameter, value, unit, ref, quote)
SCALARS = [
    ("P_KAFKA_PARTS", "Pega Kafka", "Partitions supported by the Table 1 configuration", 1000, "partitions", "P1",
     "The configuration in the preceding table can easily support up to 1000 Kafka partitions. You can increase resources accordingly if your deployment requires more Kafka partitions."),
    ("P_KAFKA_DEV_N", "Pega Kafka", "Development: instance count", 3, "brokers", "P1", "Table 1. Development 3 2 6 8 24 100"),
    ("P_KAFKA_DEV_CPU", "Pega Kafka", "Development: CPU cores per instance", 2, "cores", "P1", "Table 1. Development 3 2 6 8 24 100"),
    ("P_KAFKA_DEV_RAM", "Pega Kafka", "Development: memory per instance", 8, "GB", "P1", "Table 1. Development 3 2 6 8 24 100"),
    ("P_KAFKA_DEV_DISK", "Pega Kafka", "Development: storage per instance", 100, "GB", "P1", "Table 1. Development 3 2 6 8 24 100"),
    ("P_KAFKA_PRD_N", "Pega Kafka", "Production: instance count", 3, "brokers", "P1", "Table 1. Production 3 4 12 16 48 200"),
    ("P_KAFKA_PRD_CPU", "Pega Kafka", "Production: CPU cores per instance", 4, "cores", "P1", "Table 1. Production 3 4 12 16 48 200"),
    ("P_KAFKA_PRD_RAM", "Pega Kafka", "Production: memory per instance", 16, "GB", "P1", "Table 1. Production 3 4 12 16 48 200"),
    ("P_KAFKA_PRD_DISK", "Pega Kafka", "Production: storage per instance", 200, "GB", "P1", "Table 1. Production 3 4 12 16 48 200"),
    ("P_MSG_MAX", "Pega Kafka", "message.max.bytes required", 5000000, "bytes", "P1",
     "message.max.bytes The default maximum message size supported is 5000000."),
    ("P_REPL_FETCH", "Pega Kafka", "replica.fetch.max.bytes and replica.fetch.response.max.bytes", 5000100, "bytes", "P1",
     "replica.fetch.max.bytes ... 5000100; replica.fetch.response.max.bytes ... 5000100"),
    ("P_QP_PARTS", "Pega Kafka", "Partitions per queue processor topic (default)", 6, "partitions", "P3",
     "By default, for each queue processor, Pega Platform creates a Kafka topic with six partitions."),
    ("P_TOPIC_PARTS", "Pega Kafka", "Default partitions per topic from Pega 8.7", 6, "partitions", "P4",
     "Starting in Pega Platform version 8.7, the default number of partitions per topic is six."),
    ("P_FREE_DISK", "Pega Kafka", "Act when free disk falls below", 0.30, "fraction", "P5",
     "take actions, for example, increase disk space, when the availability of free space drops below 30%."),
    ("P_CPU_ACT", "Pega Kafka", "Consider a bigger node when average CPU is above", 0.70, "fraction", "P5",
     "If the CPU average usage is above 70%, consider provisioning a bigger node."),
    ("P_HELM_RF", "Pega Kafka", "Helm replicationFactor upper bound", 3, "replicas", "P7",
     "Your replicationFactor value cannot be more than the number of Kafka brokers and 3."),
    ("P_SEARCH_HA", "Pega search", "Minimum nodes per search service for high availability", 3, "nodes", "P2",
     "to ensure high availability, deploy Elasticsearch/OpenSearch (Master and Data nodes) and SRS with a minimum of three nodes for each service."),
    ("P_SEARCH_LARGE_GB", "Pega search", "Searchable data in the Table 4 (large) example", 2000, "GB", "P2",
     "Table 4. Recommended sizing for nodes running Elasticsearch/OpenSearch and SRS in a deployment with 2TB of Searchable Data and ~750,000 Documents"),
    ("P_SEARCH_LARGE_DOCS", "Pega search", "Documents in the Table 4 (large) example", 750000, "documents", "P2",
     "in a deployment with 2TB of Searchable Data and ~750,000 Documents"),
    ("CF_RF", "Confluent", "Replication factor (default.replication.factor, not editable)", 3, "replicas", "C3",
     "default.replication.factor ... Default: 3 Editable: No"),
    ("CF_MSG_DEFAULT", "Confluent", "Topic max.message.bytes default", 2097164, "bytes", "C3",
     "max.message.bytes ... Default: 2,097,164 ... Dedicated and Enterprise Kafka clusters maximum value: 20,971,520 Basic and Standard Kafka clusters maximum value: 8,388,608"),
    ("CF_RETENTION_H", "Confluent", "Topic retention.ms default (604,800,000 ms)", 168, "hours", "C3",
     "retention.ms ... Default: 604,800,000 Editable: Yes"),
    ("CF_STORAGE_X", "Confluent", "Billed storage relative to data written", 3, "times", "C2",
     "Because Confluent Cloud replicates data three times for high availability, billed storage is typically about 3x the volume you write."),
    ("CF_ENT_FAST", "Confluent", "Enterprise fast scaling up to", 10, "eCKU", "C1",
     "All Enterprise clusters support fast scaling up to 10 eCKU ... Beyond 10 eCKU ... approximately 20 minutes per eCKU."),
    ("CF_ENT_SCALE_MIN", "Confluent", "Enterprise on-demand scaling beyond 10 eCKU", 20, "minutes per eCKU", "C1",
     "On-demand scaling might be limited to a growth rate of approximately 20 minutes per eCKU."),
    ("CF_DED_CARD", "Confluent", "Dedicated CKU purchase limit with credit card billing", 4, "CKU", "C1",
     "For organizations with credit card billing, the upper limit is 4 CKUs per Dedicated cluster. Clusters with higher CKU limits are available by request."),
    ("CF_DED_INVOICE", "Confluent", "Dedicated CKU purchase limit with invoice or marketplace billing", 24, "CKU", "C1",
     "For organizations with integrated cloud provider billing or payment using an invoice, the upper limit is 24 CKUs per Dedicated cluster."),
    ("CF_DED_AZURE", "Confluent", "Dedicated maximum on Azure (by request)", 100, "CKU", "C1",
     "Azure supports up to 100 CKUs (available by request)."),
    ("O_SHARDS_NODE", "OpenSearch", "cluster.max_shards_per_node default", 1000, "shards", "O3",
     "cluster.max_shards_per_node (Integer): Limits the total number of primary and replica shards for the cluster ... multiplied by the number of non-frozen data nodes ... Default is 1000."),
    ("O_WM_LOW", "OpenSearch", "Low disk watermark default", 0.85, "fraction", "O3",
     "watermark.low ... OpenSearch will not allocate shards to nodes with that percentage of disk usage ... Default is 85%."),
    ("O_WM_HIGH", "OpenSearch", "High disk watermark default", 0.90, "fraction", "O3",
     "watermark.high ... OpenSearch will attempt to relocate shards away from a node whose disk usage is above the defined percentage ... Default is 90%."),
    ("O_HEAP", "OpenSearch", "Java heap as a fraction of node RAM", 0.5, "fraction", "O4",
     "Sets the size of the Java heap (we recommend half of system RAM)."),
    ("O_MANAGERS", "OpenSearch", "Dedicated cluster manager nodes for production", 3, "nodes", "O1",
     "Three dedicated cluster manager nodes in three different zones is the right approach for almost all production use cases."),
    ("A_INDEX_OVH", "AWS guidance", "Indexing overhead", 0.10, "fraction", "A1",
     "The total size of the source data plus the index is often 110% of the source, with the index up to 10% of the source data."),
    ("A_LINUX", "AWS guidance", "Linux reserved space", 0.05, "fraction", "A1",
     "By default, Linux reserves 5% of the file system for the root user"),
    ("A_SVC_OVH", "AWS guidance", "Service overhead (AWS figure; replace with your provider's figure)", 0.20, "fraction", "A1",
     "OpenSearch Service reserves 20% of the storage space of each instance (up to 20 GiB) for segment merges, logs, and other internal operations."),
    ("A_SIMPLE", "AWS guidance", "Simplified storage multiplier", 1.45, "times", "A1",
     "Source data * (1 + number of replicas) * 1.45 = minimum storage requirement"),
    ("A_SHARDS_HEAP", "AWS guidance", "Maximum shards per GiB of Java heap", 25, "shards", "A2",
     "On a given node, have no more than 25 shards per GiB of Java heap."),
    ("A_SHARD_MIN", "AWS guidance", "Shard size guideline, lower end", 10, "GiB", "A2",
     "keep shard size between 10-30 GiB for workloads where search latency is a key performance objective"),
    ("A_SHARD_MAX", "AWS guidance", "Shard size guideline, upper end (write-heavy)", 50, "GiB", "A2",
     "and 30-50 GiB for write-heavy workloads such as log analytics."),
    ("A_VCPU_100", "AWS guidance", "vCPU per 100 GiB of storage (demanding workloads)", 2, "vCPU", "A3",
     "try starting with a configuration closer to 2 vCPU cores and 8 GiB of memory for every 100 GiB of your storage requirement."),
    ("A_RAM_100", "AWS guidance", "Memory per 100 GiB of storage (demanding workloads)", 8, "GiB", "A3",
     "try starting with a configuration closer to 2 vCPU cores and 8 GiB of memory for every 100 GiB of your storage requirement."),
    ("W_BYTES_MB", "Workbook rule", "Bytes per MB when converting message rates to MBps", 1000000, "bytes", "W",
     "Decimal MB gives the larger MBps figure, so it is the cautious choice. Confluent does not state the base on the limits page."),
    ("W_BYTES_GIB", "Workbook rule", "Bytes per GiB (Confluent bills in binary GB)", 1073741824, "bytes", "C2",
     "binary gigabytes (GB), where 1 GB is 2^30 bytes. This unit of measurement is also known as a gibibyte (GiB)."),
    ("W_HOURS", "Workbook rule", "Hours in an average month (8,760 / 12)", 730, "hours", "W",
     "Used only to turn hourly and daily figures into monthly quantities for the provider quote."),
]

# Confluent per-unit limits [C1]: type -> values
CF_COLUMNS = ["Ingress MBps", "Egress MBps", "Partitions (pre-replication)", "Compacted partitions",
              "Client connections", "Requests per second", "Maximum units", "Topic max.message.bytes maximum",
              "Partition creates/deletes per 5 minutes"]
CF_NAMES = ["CF_IN", "CF_OUT", "CF_PART", "CF_COMPACT", "CF_CONN", "CF_REQ", "CF_MAXU", "CF_MSGMAX", "CF_PARTOPS"]
CF_TYPES = ["Basic", "Standard", "Enterprise", "Dedicated"]
CF_TABLE = {
    "Basic": [5, 15, 30, 30, 20, 100, 50, 8388608, 250],
    "Standard": [25, 75, 250, 250, 1000, 1500, 10, 8388608, 500],
    "Enterprise": [60, 180, 3000, 1000, 18000, 7500, 32, 20971520, 500],
    "Dedicated": [60, 180, 4500, 4500, 18000, 15000, 24, 20971520, 5000],
}
CF_NOTES = {
    "Basic": "SLA 99.5 %. Best for development, testing and basic use cases [C1].",
    "Standard": "SLA 99.9 % (1 eCKU) or 99.99 % (2 eCKU). Production workloads that use public networking [C1].",
    "Enterprise": "SLA 99.9 % (1 eCKU) or 99.99 % (2 eCKU). Production workloads that require private networking. "
                  "Azure Private Link limit 32 eCKU [C1].",
    "Dedicated": "SLA 99.95 % single-zone or 99.99 % multi-zone (minimum 2 CKU). Maximum units shown is the invoice "
                 "purchase limit; up to 100 CKU on Azure by request [C1].",
}

# Pega search sizing tables [P2]: key "profile|role|group" -> count, cpu, ram, disk
PS_ROWS = [
    ("Minimum|Master|Prod", 3, 2, 4, 0, "Table 2"), ("Minimum|Data|Prod", 3, 2, 8, 50, "Table 2"),
    ("Minimum|Master|Test", 0, 0, 0, 0, "Table 2"), ("Minimum|Data|Test", 1, 2, 8, 50, "Table 2"),
    ("Minimum|SRS|Prod", 3, 2, 2, 0, "Table 2"), ("Minimum|SRS|Test", 1, 2, 2, 0, "Table 2"),
    ("Default|Master|Prod", 3, 2, 8, 0, "Table 3"), ("Default|Data|Prod", 3, 4, 16, 100, "Table 3"),
    ("Default|Master|Test", 0, 0, 0, 0, "Table 3"), ("Default|Data|Test", 1, 2, 8, 100, "Table 3"),
    ("Default|SRS|Prod", 3, 2, 2, 0, "Table 3"), ("Default|SRS|Test", 1, 2, 2, 0, "Table 3"),
    ("Large|Master|Prod", 3, 2, 8, 0, "Table 4"), ("Large|Data|Prod", 9, 4, 16, 250, "Table 4"),
    ("Large|Master|Test", 1, 2, 8, 0, "Table 4"), ("Large|Data|Test", 4, 4, 16, 250, "Table 4"),
    ("Large|SRS|Prod", 3, 2, 2, 0, "Table 4"), ("Large|SRS|Test", 1, 2, 2, 0, "Table 4"),
]

# Maximum partitions per broker by machine type [P5]
PM_ROWS = [(2, 2, 300), (2, 8, 1000), (4, 16, 1000), (8, 32, 2000), (16, 64, 4000)]

LANDSCAPES = ["Development", "Testing", "Stage", "Production"]
OS_VERSIONS = ["OpenSearch 1.3", "OpenSearch 2.15", "OpenSearch 2.19", "Other"]

PEGA_KAFKA_SETTINGS = [
    ("message.max.bytes", "5000000", "On Confluent Cloud, set the topic max.message.bytes; the topic default is 2,097,164 [C3]."),
    ("replica.fetch.max.bytes", "5000100", "Broker setting managed by Confluent; confirm the equivalent [C3]."),
    ("replica.fetch.response.max.bytes", "5000100", "Broker setting managed by Confluent; confirm the equivalent [C3]."),
    ("unclean.leader.election.enable", "false", "Confirm with Confluent."),
    ("auto.create.topics.enable", "false", "Confirm with Confluent."),
]

PEGA_ACLS = [
    ("TOPIC", "Prefixed (stream name pattern prefix)", "ALL"),
    ("GROUP", "Prefixed (stream name pattern prefix)", "ALL"),
    ("TRANSACTIONAL_ID", "*", "ALL"),
    ("CLUSTER", "kafka-cluster", "IDEMPOTENT_WRITE"),
]

PEGA_TABLE4_NOTE = ("Pega Table 4 lists 9 data nodes at 16 GB each with a total of 136 GB; 9 x 16 is 144 GB. "
                    "It also lists 9 x 250 GB = 2,250 GB of data-node disk for 2 TB of searchable data, which is less "
                    "than the AWS storage formula gives with one replica. The workbook uses the per-node figures and "
                    "calculates storage separately; ask Pega to confirm Table 4 if you rely on it.")
