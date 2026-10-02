# Master prompt: Pega Platform 26.1.1 on Azure AKS with Confluent Cloud Kafka and managed OpenSearch, built from a cloned and upgraded Pega 8.8 database

Version 3.1. Use this prompt as the complete brief for producing the customer document. Every instruction in it is mandatory unless it says "should".

---

## 1. Your role

You are writing as the delivery lead of a team that has already done this kind of implementation for other clients. The team has these members:

- a Pega Lead System Architect who has moved Pega 8.x clients to Pega Platform '25 and '26 on Kubernetes, with external Kafka and SRS;
- a DevOps engineer who runs the Pega Helm charts pipeline on AKS, including the installer job for database upgrades;
- an Azure cloud architect who owns private networking, DNS and Key Vault;
- a database administrator who has cloned and upgraded Pega databases;
- a Kafka engineer who runs Confluent Cloud for several applications;
- an OpenSearch engineer who runs shared search clusters.

You write for the customer's IT teams: architects, platform engineers, DBAs, Kafka and search operators, security, and test leads. They will build and run what you describe, so they must be able to follow every step without guessing.

## 2. The programme and where this document fits

### 2.1 How the programme moves from 8.8 to 26.1.1

The customer is upgrading an existing Pega Platform 8.8 system. They are not upgrading the running 8.8 servers in place. They are using a **clone-and-upgrade** path:

1. **Build the new platform.** Pega 26.1.1 runs on Azure AKS through the Pega Helm charts. It is configured from the start with externalized services: Kafka on **Confluent Cloud**, and search through the Pega **Search and Reporting Service (SRS)** backed by a **managed OpenSearch service**.
2. **Clone the database.** The current 8.8 Pega database (rules and data schemas) is cloned.
3. **Upgrade the clone.** The cloned database is upgraded to 26.1.1 with the Pega 26.1.1 installer, run as the Helm chart installer job.
4. **Start Pega on the upgraded database.** The 26.1.1 environment on AKS runs on the upgraded database and connects to Confluent Cloud and OpenSearch.
5. **Repeat per environment.** Lower environments are built the same way, for rehearsal and testing.
6. **Cut over production.** Production uses a final clone, taken when 8.8 is stopped. The 8.8 system and its database stay untouched until rollback is no longer needed.

### 2.2 What this document covers

The document covers the **Kafka and search part of this programme, end to end**:

1. Designing and configuring Confluent Cloud and managed OpenSearch for Pega 26.1.1 in each of the six environments: DEV, SIT, UAT, PERF, PREPROD and PROD (section 2.5).
2. Configuring both in the **Pega Helm charts** (`pega` chart `stream` and `pegasearch` sections; `backingservices` chart for SRS) as part of the 26.1.1 deployment. Do not describe configuring them afterwards in the Pega UI, except for checks and settings that only exist there.
3. **What the cloned 8.8 database brings with it** that affects Kafka and search, and what must be changed, removed or checked before and after the first 26.1.1 start (section 4).
4. Whether Kafka topics and search indexes must be migrated from 8.8, and how in-flight 8.8 work is handled at cutover (section 5).
5. **Sharing services in non-production**, with strict isolation between environments, to reduce cost. Production always has its own Kafka cluster and its own OpenSearch service. Work out the non-production split with a decision diagram and the cost model, starting from this default:
   - **Shared group 1, functional:** DEV, SIT and UAT share one Confluent cluster and one OpenSearch service.
   - **Shared group 2, production-like:** PERF and PREPROD share a second Confluent cluster and OpenSearch service of the same type, settings and private networking as production. Load tests and production rehearsals then run on production-like services without affecting the functional environments. PERF and PREPROD runs are scheduled so they do not overlap.
   - Also assess the alternatives: all five non-production environments on one shared set, or PREPROD on its own set. Recommend one option, and give the reasons.
6. Testing, failure scenarios, known issues, troubleshooting and operations for Kafka and search.

### 2.3 Covered only as dependencies

Describe each of these only to the depth needed to show how it affects Kafka and search. Name the owner, the gate it must pass, and the source.

- The database clone and the installer upgrade itself: schema handling, `installer.upgrade.upgradeType`, and installer logs.
- Pega's '25 and later prerequisites that apply to the upgraded database:
  - Hazelcast removal;
  - Tomcat 10.1 and Jakarta changes to custom CodeSets and JARs;
  - primary keys on all tables;
  - changes to queue processor Dynamic System Settings (DSS).

### 2.4 Out of scope (state this in the document)

- Application functional regression content.
- Cassandra and Decision Data Store.
- Constellation.
- Pega Diagnostic Center beyond the connectivity it needs.
- General AKS build-out not related to Kafka or search.

### 2.5 Confirmed customer inputs

Use these facts throughout. Do not present them as assumptions.

| Input | Value | What it means for the document |
|---|---|---|
| Environments | DEV, SIT, UAT, PERF, PREPROD, PROD | Six columns in every per-environment table, plus six prefixes, six service accounts, six `customerDeploymentId` values, six OAuth clients and six sets of Key Vault secrets. |
| 8.8 Kafka | Embedded Kafka (the Pega stream service running inside 8.8) | Nothing in embedded Kafka can be moved to Confluent Cloud. 8.8 queues are emptied by stopping intake and letting processing finish before the final clone. The Stream Migration activity is a tool for switching a running 8.8 to an external Kafka, which this programme does not do. Explain why it is not used. The cloned database carries 8.8 stream settings and stream node records that must be cleaned up (section 4.2). |
| 8.8 search | Embedded Elasticsearch | The 8.8 indexes live on the 8.8 search nodes' disks, not in the database, so they cannot be carried over. 26.1.1 builds all indexes through SRS from the upgraded database. The cloned database carries 8.8 search settings and index host node settings that must be cleaned up or checked. Check for any search-dependent application features (custom search properties, reports or rules that rely on search), and confirm that each one works with SRS. |
| Identity provider for Pega-to-SRS tokens | Okta | Design the SRS token setup on Okta (section 6.3). |
| OpenSearch provider | Not chosen yet | Include a provider selection method and comparison, write Helm values that do not depend on the provider, and make the choice an open decision with a due date. |
| Pega Support answers on the gating questions | Not received | Treat every gating question in section 4.1 as open, with an owner and a due date. The production plan must not depend on an unconfirmed answer. |

## 3. Questions the document must answer

Answer each one directly, in its own clearly titled section or table row, and cite evidence for each answer.

1. Is the clone-and-upgrade path from 8.8 directly to 26.1.1 supported by Pega? What conditions apply?
   - Check the supported source versions for the 26.1.1 installer.
   - Check whether the "remove Hazelcast before updating to '25 or later" requirement applies when the old runtime never runs on the upgraded database.
   - Record anything Pega Support must confirm in writing (section 4.1).
2. How is Confluent Cloud designed for Pega 26.1.1? Cover cluster type, networking, security, topics, partitions and sizing, per environment.
3. How is the managed OpenSearch service designed? Cover the provider choice, a version on the Pega SRS compatibility matrix, cluster settings, sizing, security and backups, per environment.
4. How exactly is each one configured in the Helm charts, for both the installer (upgrade) run and the deploy run? Show every key, its value per environment, and where each secret comes from.
5. What does the cloned 8.8 database contain that conflicts with, or overrides, the new Kafka and search configuration? How is each item cleaned up?
6. How is a cloned non-production environment stopped from connecting to production Kafka topics, production integrations, or another environment's data?
7. Once 26.1.1 is configured, must Kafka topics or search indexes be migrated from 8.8? How is 8.8 in-flight work handled at the production cutover?
8. How do several non-production Pega environments share one Kafka cluster and one OpenSearch service without affecting each other, and how is each environment's data kept apart?
9. How much does sharing save, and what risks does it add? Give a cost comparison model with the inputs the customer must supply. Do not invent prices.
10. How do we test it? Cover connectivity, functional checks, isolation between environments, performance, failures and recovery, security, and the full rehearsal of clone, upgrade, start and reindex.
11. Which failures must be tested? For each one, how is it caused, what should Pega do, how is the failure detected, and how does the system recover?
12. What are the known issues and challenges from real implementations, and how are they avoided?
13. How is it run day to day? Cover monitoring, alerts, rotation, capacity, onboarding a new environment, refreshing an environment from a new clone, and retiring an environment.

## 4. The cloned database: what it brings and what must change

This is the part a generic document would miss, so treat it with the most care.

### 4.1 Gating questions for Pega Support

Present these as a table: question, why it matters, evidence found, the answer received, and the date. The Pega pages read so far say that Hazelcast must be removed before updating to '25 or later, and that the change affects both embedded Hazelcast and the Clustering Service. They do not say how this applies to a cloned database that is upgraded offline and started only on a '26 runtime.

Do not assume an answer. Raise a Pega Support request, and record any condition Pega sets (for example, settings that must exist in the database before the upgrade) as a mandatory step in the rehearsal runbook. Ask the same way about:

- the supported source versions for a direct upgrade;
- any required 8.8 patch level;
- the upgrade type that suits a cloned database: in-place on the clone, or out-of-place. Use the `installer.upgrade.upgradeType` values the Helm chart documents.

### 4.2 Inventory of Kafka and search items in the cloned database

Before writing the inventory, check in Pega '26 and 8.8 documentation where each item is stored and how 26.1.1 treats it. Give a table with:

- the item;
- where it lives: a database table, a DSS, a data instance or a rule;
- what 26.1.1 does with it;
- the risk;
- the action: keep, change, delete or check;
- when the action happens: before the upgrade, after the upgrade but before the first start, or after the first start;
- the evidence.

Cover at least:

- **Stream and search settings in the database.**
  - Stream service DSS and prconfig-style DSS from 8.8: the stream provider, broker URL, name pattern and replication.
  - Explain the order of precedence between Helm-supplied settings and DSS values in the database, and say which one wins. If the documentation does not settle this, make it a rehearsal test.
  - Search DSS and settings from 8.8 embedded Elasticsearch: index host node settings, and search node records. Confirm that 26.1.1 uses SRS as configured in Helm, and that no 8.8 search setting overrides it.
  - Embedded stream settings from 8.8: Stream node records and any DSS that describe the embedded stream service. Confirm that 26.1.1 uses Confluent Cloud as configured in Helm.
- **Leftover stream and indexing records.** Stream node records and decisioning service node records from 8.8, and any search index status or indexing queue records.
- **Queue processor items.** Delayed items, and broken items held in database tables. Count them before the clone, and decide whether to resolve, discard or reprocess each kind on 26.1.1.
- **Scheduled and data flow work.**
  - Job scheduler definitions and their next-run state.
  - Data flow run records, including any partition or offset state that refers to 8.8 topics. Decide which runs are restarted, and from where.
- **Application Kafka connections.**
  - Kafka configuration instances and Kafka data sets that point to the customer's own Kafka clusters.
  - In a cloned non-production environment, these still point to wherever 8.8 production points. Repoint or disable them **before the first start**.
- **Other production endpoints in the database.** Connectors, listeners and email accounts that could reach production systems from a cloned environment. Cover them only as a short checklist, with the owner named.
- **Queue processor DSS that '26 no longer uses.** Settings such as `delayeditems/dataflowbased/threadspernode`, which Pega '26 says must be removed (PEGA0179).

### 4.3 "First start" control for every cloned environment

The document must define a scripted sequence for the first start of each environment built from a clone:

1. Upgrade the clone.
2. Apply the database clean-up (section 4.2) with a reviewed SQL or Pega-supported method. Say which method Pega supports for each item, and do not invent table names.
3. Deploy the 26.1.1 tiers with this environment's own Kafka prefix, credentials and `customerDeploymentId`.
4. Hold the application intake. Keep listeners, job schedulers and queue processors that call external systems disabled until the checks pass.
5. Check the Stream and search landing pages.
6. Run the full index build.
7. Release the intake.

Each step has an owner, a check and the evidence to keep.

### 4.4 Data protection

Non-production clones of production data must follow the customer's data masking policy. State where masking happens: before the upgrade, after it, or at the clone. Note that search indexes are built from the masked data only if masking happens before indexing.

## 5. The 8.8 migration question: evidence you must use and explain

Answer the question "is there a requirement to migrate Kafka topics and search indexes from 8.8?" in a dedicated section. It needs a decision diagram and a table with one row per content type. Check each statement below against the current Pega documentation before using it. If a statement has changed, use the current text and record the change.

| Content | Expected answer | Evidence to check |
|---|---|---|
| Pega stream data in Kafka: queue processor messages, data flow stream partitions | **Not migrated.** Pega states that existing stream data cannot be moved to a new Kafka. Before the production clone is taken, stop intake on 8.8 and let queue processors finish. 8.8 uses embedded Kafka, so there is no drain-to-external step. Hold intake, wait until queue processors show nothing ready to process, record the counts (and any broken items) as evidence, then stop 8.8. 26.1.1 starts with empty topics that it creates itself. | Pega docs: "Switching Kafka providers while preserving Stream data"; Helm charts: `MigrationToExternalStream.md` |
| Queue items held in the database (for example delayed or broken items) | **Travel with the clone.** These are database content, not Kafka content. Check how 26.1.1 treats them after the upgrade (section 4.2), and test it in rehearsal. | Pega docs on queue processors and delayed processing |
| Topic names and configuration | **Not migrated.** 26.1.1 creates its own topics under its own `streamNamePattern` prefix. Only the topic settings policy, such as `max.message.bytes`, is carried over, as configuration. | Pega docs: "External Kafka in your deployment" |
| Search indexes (embedded Elasticsearch on 8.8) | **Not migrated.** The embedded indexes live on the 8.8 nodes, not in the database. Indexes are built from the upgraded database after Pega connects to SRS. Pega states this needs a downtime period, so measure the time in rehearsal and fit it into the cutover plan. Elasticsearch 8.x snapshots cannot be restored into OpenSearch. | Pega docs: "Connecting Pega Platform to SRS", "Rebuilding search indexes"; OpenSearch migration documentation |
| Application Kafka integrations (Kafka data sets on the customer's own topics) | **Decided per data set.** Choose one: keep the existing topic and cluster, point at a new cluster, or mirror (for example with Confluent Cluster Linking, which keeps offsets). Agree the start offset, so that messages are neither skipped nor processed twice at cutover. | Pega docs: Kafka data sets; Confluent Cluster Linking documentation |
| Custom search data (custom indexes, reports that depend on search) | Rebuild and verify on 26.1.1 with a count comparison against the database. | Pega docs: index status and reindex pages |

The section must end with a short, firm statement the customer can approve, for example: "No Pega stream topic and no search index is copied from 8.8. Database-held queue items travel with the clone and are handled as listed in Table X. Application Kafka topics are handled one by one as listed in Table Y."

## 6. Detailed content required

### 6.1 Architecture

- **Pega's official images.** Show the 26.1.1 architecture using Pega's own images, credited to their source pages, from:
  - Pega docs, "Pega Platform Kubernetes architecture";
  - Pega docs, "External Kafka in your deployment" (Kafka use cases);
  - Pega docs, "External Search in your deployment" and the SRS pages;
  - the Pega Helm charts zero-downtime and upgrade documentation, for schema diagrams if used;
  - Pega Academy topics on deployment architecture with external services and on the Search and Reporting Service.
- **New diagrams.** Draw these as clean, consistent architecture diagrams:
  1. Target architecture on Azure: AKS, Pega tiers, installer job, SRS, Application Gateway, private endpoints, the Confluent Cloud network, the managed OpenSearch endpoint, Key Vault, the External Secrets Operator, the hub firewall, and the upgraded database.
  2. The clone-and-upgrade flow: 8.8 production, its database, the clone, masking (for non-production), the installer upgrade, clean-up, the 26.1.1 deployment, the index build, and release.
  3. The production cutover timeline: 8.8 intake stop, drain, final clone, upgrade, first start, index build, checks, DNS switch, and the rollback point.
  4. Shared non-production topology: the recommended non-production grouping (for example DEV, SIT and UAT on one set, and PERF and PREPROD on a second production-like set), showing the prefix, service account, ACL, index prefix and credential boundaries.
  5. Production topology, with its dedicated services.
  6. Network and DNS flow for Confluent Private Link and the OpenSearch private endpoint.
  7. Secret flow: Key Vault, then the External Secrets Operator, then Kubernetes secrets, then the Pega, installer and SRS pods.
  8. The OAuth token flow between Pega, the identity provider and SRS, including the `guid` claim check.
  9. The message path inside Pega: queue processor, topic, consumer group, partition, and the batch tier.
- **Decision diagrams.** Include one for each of:
  - the Confluent cluster type;
  - shared or dedicated services per environment;
  - one SRS per environment or one shared SRS;
  - the OpenSearch provider;
  - Kafka authentication;
  - the treatment of each cloned-database item (section 4.2);
  - whether to migrate 8.8 content;
  - the treatment of application Kafka data sets;
  - go or no-go at the first start;
  - troubleshooting Kafka;
  - troubleshooting search.

### 6.2 Confluent Cloud design

- **Pega's requirements mapped to Confluent Cloud**, one row per requirement:
  - message size settings;
  - replication and unclean leader election;
  - automatic topic creation;
  - supported security mechanisms;
  - required ACLs (TOPIC and GROUP on the prefix, TRANSACTIONAL_ID, CLUSTER IDEMPOTENT_WRITE);
  - client compatibility (the Kafka client version in 26.1.1);
  - the minimum Confluent version.

  For each, say whether Confluent Cloud allows it, what the customer does, and the evidence. Where Confluent manages a broker setting the customer cannot change, say so and turn it into a question for Confluent support.
- **Cluster type comparison** (Basic, Standard, Enterprise, Dedicated, and Freight where relevant). Use Confluent's published limits for ingress, egress, partitions, private networking and features. Explain why Freight does not suit Pega if it lacks idempotent producers or transactions. Give a recommendation for non-production and one for production.
- **Networking.** Cover Azure Private Link (or the private option available for the chosen type), the private DNS zone and its records, and steps to test resolution from an AKS pod.
- **Security.** One service account per environment, with API keys held in Key Vault. Give the JAAS string format, the exact prefixed ACLs, and the Confluent CLI commands to create, list and remove them. Explain why wildcard ACLs are forbidden on the shared cluster.
- **Topic design.**
  - Naming pattern per environment, for example `pega-dev-{stream.name}` and `pega-sit-{stream.name}`. When an environment is rebuilt from a new clone, explain whether to reuse its prefix (after deleting the old topics) or to use a new one.
  - Replication factor and `max.message.bytes`.
  - Who creates topics: Pega through the admin client, or pre-created topics if policy forbids creation rights.
  - The topics Pega '25 and later need for clustering after Hazelcast removal (verify the list).
- **Partition budget.** Give a method that measures partitions per environment after the first full start, then adds headroom. Show a worked table with placeholders for the measured numbers, and compare the total with the cluster limit.
- **Quotas and noisy neighbours.** Cover client quotas per service account where the cluster type supports them (verify availability), producer and consumer limits, and what to do if one environment's load test affects the others.

### 6.3 Managed OpenSearch design

- **Provider options on Azure.** Azure has no first-party managed OpenSearch, so compare third-party managed providers that run on Azure with self-managed OpenSearch on AKS. Assess each on:
  - an OpenSearch version on the SRS matrix;
  - private connectivity;
  - settings control (`action.auto_create_index`, `action.destructive_requires_name`);
  - fine-grained access control;
  - snapshots;
  - support terms.

  Do not name prices. Name only providers whose own documentation shows an Azure region and an OpenSearch version on the SRS matrix, and cite that documentation. Give a scored selection table the customer can fill in, and write the Helm values and the runbook so that they work with any provider that passes the selection (endpoint, port, credentials and CA are the only provider-specific values).
- **SRS compatibility.** Give the SRS image and OpenSearch versions certified for 26.1.1, with the image name `search-n-reporting-service-os`. Where the Pega documentation and the Helm chart README disagree, record the conflict and follow the stricter source.
- **Cluster settings and sizing.**
  - Give the required cluster settings with the exact API call.
  - Base sizing on Pega's published sizing tables and on the searchable data volume measured in the upgraded database.
  - Cover shards and replicas per index, the shard budget per node, and disk watermarks.
- **Isolation in the shared non-production service.**
  - A distinct `customerDeploymentId` per environment, which becomes the index prefix. Explain why a cloned environment must never reuse another environment's ID.
  - One SRS per environment (recommended for isolation) or one shared SRS. Compare credentials, blast radius, upgrades and cost.
  - An OpenSearch role per environment restricted to that environment's index pattern, if SRS works with index-scoped permissions. Verify whether SRS needs cluster-level privileges and state the result.
  - Clean-up of indexes when an environment is refreshed from a new clone or retired.
- **Pega-to-SRS tokens with Okta.** Design and verify each of the following against current Okta documentation and the Pega SRS pages:
  - **Where tokens come from.** Pega uses the OAuth client credentials grant, with `private_key_jwt` (recommended) or `client_secret_basic`, and the scope `pega.search:full`. Use an Okta custom authorization server, because custom scopes and custom claims need one. Confirm whether the customer's Okta licence includes custom authorization servers.
  - **The `guid` claim.** SRS checks that the token's `guid` claim equals the environment's `customerDeploymentId`. Choose how Okta issues a different value per environment:
    - one custom authorization server per environment, with a fixed `guid` claim; or
    - one server with a claim expression based on the client. Only choose this if Okta documents that the expression works for client credentials tokens.

    Recommend one option, and prove it by decoding a token in DEV.
  - **Okta set-up per environment.** One Okta API service application per environment. Register the public key for `private_key_jwt`, and keep the private key in Key Vault as `SRS_OAUTH_PRIVATE_KEY`.
  - **Pega and SRS settings.** The token endpoint and key set (JWKS) URL formats for an Okta custom authorization server, set as `pegasearch.srsAuth.url` and `srsRuntime.env.OAuthPublicKeyURL`.
  - **Network path.** SRS pods must reach the Okta JWKS URL, and Pega pods must reach the Okta token URL, both through the egress firewall. Okta is a public SaaS endpoint, so list the firewall rule.
  - **Token checks and rotation.** Token lifetime and how often Pega requests tokens. Whether SRS checks issuer and audience. Key rotation steps on both sides.
  - **Failure tests:** Okta unreachable, the key rotated in Okta but not in Key Vault, and a wrong `guid` value.
- **Index build planning.**
  - Measure the full build time in each rehearsal and record it against data volume.
  - Give the method to estimate production time from the rehearsal figures.
  - State the checks for completeness: index status per class, document counts against database counts, and any CONFLICTS FOUND status.
- **Backups and restore.** Explain that indexes can always be rebuilt from the Pega database. Snapshots shorten recovery but are optional, so state the recovery time for each choice.

### 6.4 Helm configuration, per environment

- **Every key**, in one table per chart:
  - for the `pega` chart:
    - `global.actions.execute` for the upgrade run and the deploy run;
    - `installer.upgrade.*`;
    - `global.jdbc` pointing at the upgraded clone;
    - `global.customerDeploymentId`;
    - the `stream.*` keys;
    - `pegasearch.*`, including `srsAuth` and `srsMTLS`;
    - `external_secret_name`;
    - the tier settings that matter for Kafka consumers;
    - the `hazelcast` keys as Pega requires for '26;
  - for the `backingservices` chart: `srsRuntime`, `srsStorage` and `networkPolicy`.

  Columns: key, meaning, DEV, SIT, UAT, PERF, PREPROD, PROD, and source.
- **Complete, valid YAML** values files for one non-production environment and for production, for both the upgrade run and the steady-state deploy. Check every key against the Helm chart README of the chart version used, and state that version.
- **The secret inventory.** Give the exact key names the charts require (`STREAM_TRUSTSTORE_PASSWORD`, `STREAM_KEYSTORE_PASSWORD`, `STREAM_JAAS_CONFIG`, `SRS_OAUTH_PRIVATE_KEY`, `DB_USERNAME` and `DB_PASSWORD`, and the SRS storage `username` and `password`), the Key Vault names, and the External Secrets Operator manifests.
- **Build order and checks**, with a check after each step: network and DNS, then secrets, Confluent, OpenSearch, SRS, the database clone, the installer upgrade, the database clean-up, the Pega deploy with intake held, the index build, and intake release.

### 6.5 Testing

- **Test stages.** For each stage, give the entry criteria, the environment, the owner and the evidence produced. Cover:
  - connectivity, configuration and functional tests;
  - isolation, performance, resilience and security tests;
  - operational acceptance;
  - **full rehearsals of the clone-and-upgrade path**, at least two before production, on production-sized data.
- **Rehearsal measurements.** Measure, and record against data volume:
  - drain time on 8.8;
  - clone time;
  - upgrade time;
  - clean-up time;
  - first start time;
  - full index build time;
  - time to release intake.
- **Isolation tests.** Prove that environment A cannot read, write or delete environment B's topics, consumer groups or indexes, using negative tests with A's credentials. Prove that no cloned environment reaches production Kafka topics or production integrations.
- **Failure scenario catalogue**, at least 25 rows. Columns: ID, scenario, how to cause it safely, expected Pega behaviour, detection (log message, alert, landing page), recovery, and pass criteria. Include at least:
  - **Kafka access:**
    - the Kafka bootstrap host cannot be reached;
    - the private DNS record is wrong or missing;
    - the API key is revoked;
    - an ACL is missing for a new topic;
  - **Kafka capacity and load:**
    - the partition limit is reached;
    - a message is larger than `max.message.bytes`;
    - a broker rolling restart happens during Confluent maintenance;
    - consumer lag builds up under load;
  - **SRS:**
    - an SRS pod or the whole SRS deployment is lost;
    - an OAuth token cannot be obtained;
    - the `guid` claim does not match `customerDeploymentId`;
  - **OpenSearch:**
    - cluster status goes yellow, then red;
    - the disk flood-stage watermark makes indexes read-only;
    - the OpenSearch credentials are rotated;
  - **Platform:**
    - a certificate expires;
    - a Key Vault secret is rotated without a pod restart;
    - an AKS node is drained, or an availability zone is lost;
  - **Shared services:**
    - a non-production load test saturates the shared cluster;
    - an index rebuild runs during business hours;
    - a wrong `customerDeploymentId` is deployed by mistake;
  - **Clone-specific:**
    - a stale 8.8 stream or search DSS in the cloned database overrides the Helm configuration;
    - a cloned environment starts with application Kafka data sets still pointing to production;
    - delayed or broken queue items from 8.8 are processed unexpectedly on 26.1.1;
    - the installer upgrade fails halfway (resume or restart, per the Helm chart guidance);
    - the index build is interrupted.
- **Exact checks.** For each check, give the command or screen: the Stream landing page, queue processor status, the search landing page, the Confluent CLI, `kcat`, the OpenSearch `_cluster/health`, `_cat/indices` and `_cluster/settings` APIs, the installer job logs, and `kubectl`.

### 6.6 Known issues and challenges

Write these as experience-based guidance: the symptom, the cause, how to prevent it, and how to fix it. Include at least:

- **Cloned database:**
  - The cloned environment silently uses 8.8 settings from the database instead of the Helm values.
  - Application Kafka consumers in a test environment read production topics and move their consumer offsets, which affects production.
  - Leftover 8.8 stream node and index records confuse the landing pages.
  - Queue items from 8.8 fail on 26.1.1 because the rules they reference changed.
  - The index build is slower than planned on production-sized data.
- **Kafka and Confluent:**
  - Clients reach the bootstrap server but fail on broker connections because broker names resolve to public IPs (Private Link DNS).
  - Too many partitions from many queue processors on a shared cluster.
  - The Confluent topic message size default is lower than Pega's requirement.
  - A JAAS string is stored with the wrong quoting.
  - A secret is changed but pods were not restarted.
  - Topic creation is denied because the policy forbids CREATE.
  - From '25, Pega uses Kafka for cluster messaging that Hazelcast used to carry, so a Kafka outage affects more than queue processing. Verify this and explain the consequence.
- **OpenSearch and SRS:**
  - Indexes are auto-created with the wrong settings, or index auto-creation is blocked.
  - Okta tokens do not carry what SRS checks: the scope is missing, the `guid` claim is missing or has the wrong value, or the token comes from the Okta org authorization server instead of a custom authorization server. Give the symptom in the SRS and Pega logs, and the fix.
  - An SRS image version is not on the matrix for the OpenSearch version.
  - Indexes are orphaned after an environment is refreshed with a new `customerDeploymentId`.
- **Process:** a non-production refresh from a new production clone. Masking, a new or cleaned prefix and index ID, repointed integrations, and a full reindex are required every time.

### 6.7 Cutover and rollback (Kafka and search view)

- Give the production cutover sequence from the Kafka and search point of view:
  - 8.8 intake stop, drain and the zero-count evidence;
  - the final clone;
  - the upgrade and clean-up;
  - the first start with intake held;
  - the index build and checks;
  - the cutover of application Kafka data sets (offset handling);
  - DNS switch and intake release.
- Rollback restarts 8.8 on its untouched database, with its original Kafka and search. State the point after which rollback loses work done on 26.1.1, and how the business decides whether to accept that.

### 6.8 Operations

- A monitoring table: the signal, its source (Confluent Metrics API, provider metrics, SRS logs, Pega alerts), the threshold and the response.
- Routine tasks with frequency and owner: API key rotation, certificate renewal, partition and shard capacity review, SRS image updates, OpenSearch version updates, and cost review.
- Onboarding a new non-production environment onto the shared services, as a numbered checklist.
- Refreshing an environment from a new clone, as a numbered checklist.
- Retiring an environment, as a checklist: delete the ACLs, service account, topics, consumer groups, indexes, OpenSearch role and secrets, and record evidence.
- A RACI between the customer platform team, DBA team, Kafka team, search team, Pega team, Pega Support, Confluent and the OpenSearch provider.

### 6.9 Risks, open decisions, assumptions

- A risk register with likelihood, impact, mitigation and owner.
- Open decisions, each with options, a recommended answer, an owner and the date by which it is needed:
  - Pega Support answers on the gating questions (section 4.1);
  - Confluent cluster types;
  - the OpenSearch provider;
  - SRS per environment or shared;
  - the Okta design: one custom authorization server per environment, or one shared server;
  - the environment list;
  - the masking approach;
  - the treatment of each application Kafka data set;
  - the quota approach.
- Assumptions, each with the check that would prove it wrong.

## 7. Evidence rules

1. **Every product statement must cite a source** in square brackets, such as [R7], resolving to a numbered reference list with full URLs. Use, in order of authority:
   - Pega documentation for Pega Platform '26, and for 8.8 where the topic is 8.8 behaviour;
   - the Pega Helm charts GitHub repository (state the chart version);
   - Pega Academy;
   - Confluent Cloud documentation;
   - OpenSearch documentation and the chosen provider's documentation;
   - Microsoft Learn.
2. **Read each page before citing it**, and record the date it was read.
3. **If no source settles a point**, say so plainly and turn it into a test in the test plan, a Pega Support question, or an open decision. Never fill the gap with an assumption written as fact.
4. **Do not invent database table names, DSS names, activity names or API paths.** Use only names found in Pega documentation or confirmed by Pega Support.
5. **Record conflicts between sources** in a reconciliation table: the topic, what each source says, and the decision taken.
6. **Do not state version numbers, limits or defaults from memory.** Copy them from the cited page.
7. **Pega and third-party images** must carry a source line under the figure. An appendix lists every image with its page and a note that reuse rights must be confirmed before external distribution.

## 8. Writing rules

- **Plain English.** Short sentences in the active voice, one idea per sentence. Write the way an experienced engineer explains a design to a colleague.
- **Explain every table** in the text before or after it: what it shows and what the reader should do with it. Number and caption every table and figure, and refer to them by number.
- **Use precise verbs and real nouns**: "set", "create", "check", "restart", "the batch tier", "the service account", "the cloned database".
- **Do not use these words or patterns:**
  - leverage, seamless, robust, comprehensive, cutting-edge, state-of-the-art, holistic, synergy, empower, unlock, elevate, streamline, delve, navigate (except for UI navigation), landscape (except Pega's sizing column name), journey, game-changer, best-in-class, world-class, crucial, vital, pivotal, paramount;
  - "it is important to note", "in today's", "in conclusion", "overall", "furthermore", "moreover";
  - em dashes, rhetorical questions, exclamation marks, and marketing claims.
- **Do not write sentences that say nothing**, such as "This section describes...". Start with the fact.
- **Keep naming consistent.** Use one name per concept and the same environment codes, IDs and prefixes everywhere.
- **Use requirement words carefully.** "Must" is for vendor requirements and fixed decisions only. "Should" is for recommendations.
- **Use angle brackets for environment-specific values** in commands and YAML, for example `<bootstrap-host>`. List each one in the configuration inventory appendix.

## 9. Document structure and format

Produce a Word document (DOCX) with an A4 page, a header with the short title, and a footer reading "Customer Confidential | Page X of Y". It must have:

1. **Front matter:**
   - a cover page;
   - document control: version, status, date, evidence cut-off date and owner;
   - revision history;
   - approvals with signature rows;
   - a table of contents with page numbers;
   - a list of figures;
   - a list of tables.
2. **Executive summary:**
   - the clone-and-upgrade approach in one paragraph;
   - the Kafka and search design;
   - the cost-sharing approach;
   - the answer to the migration question;
   - the gating questions for Pega Support;
   - the decisions needed.
3. Scope, dependencies, assumptions and reading guide by role (section 2).
4. Evidence baseline: versions and support facts with sources.
5. Architecture (6.1).
6. Shared and dedicated service model, with isolation and cost.
7. Confluent Cloud design and configuration (6.2).
8. Managed OpenSearch and SRS design and configuration (6.3).
9. Secrets, certificates and identity.
10. Helm configuration per environment, for the upgrade run and the deploy run (6.4).
11. The cloned database: gating questions, inventory, clean-up and first-start control (section 4).
12. The 8.8 content question: decision and treatment (section 5).
13. Deployment runbook per environment, with numbered steps, owner, check and evidence.
14. Production cutover and rollback (6.7).
15. Test strategy, rehearsals and failure scenarios (6.5).
16. Known issues and challenges (6.6).
17. Troubleshooting, with decision trees and symptom tables.
18. Operations, onboarding, refresh and retirement (6.8).
19. Risks, open decisions, assumptions and source reconciliation (6.9, 7.5).
20. **Appendices:**
    - A. Configuration inventory per environment.
    - B. Complete Helm values files (upgrade run and deploy run).
    - C. Command reference.
    - D. Evidence, rehearsal and test record templates.
    - E. Glossary.
    - F. References with links.
    - G. Image sources and attribution.

Expected size: 80 to 110 pages. Diagrams must be legible when printed on A4. Code blocks must not wrap.

## 10. Acceptance checks before release

The document is complete only when every check passes. Report the result of each check with the document.

1. Every [Rn] resolves to the reference list, and every reference is cited at least once.
2. Every section, figure and table cross-reference points to the right target.
3. No banned words or patterns (section 8), and no placeholder text other than angle-bracket values listed in Appendix A.
4. Every YAML block parses, and every Helm key exists in the chart version stated.
5. Every command has been checked for correct syntax for the tool version stated.
6. Every question in section 3 has a findable answer. Give a traceability table from question to section.
7. Every failure scenario has its cause, expected behaviour, detection, recovery and pass criteria filled in.
8. Every cloned-database item in section 4.2 has a source, an action and a time point.
9. Every Pega or third-party figure has a source line.
10. The reviewer checklists (section 11) are completed, and their findings are fixed or logged.

## 11. Expert review before release

Review the finished document once from each viewpoint below. Fix what you find, and list the findings and fixes in a short review log, which is kept out of the customer copy.

| Reviewer | Must confirm |
|---|---|
| Pega Lead System Architect | Stream and search behaviour matches Pega '26 documentation; the clone-and-upgrade gating questions are complete; the cloned-database inventory and first-start control are correct; the migration decision is correct; `customerDeploymentId` handling is safe |
| DevOps engineer | Helm keys and YAML are valid for the stated chart version, for both the upgrade and deploy runs; the build order works; secrets never appear in values files; the pipeline steps are repeatable per environment and per refresh |
| Database administrator | The clone, masking, upgrade and clean-up steps are safe and repeatable; no invented table names; rollback keeps the 8.8 database untouched |
| Azure cloud architect | Private Link and private endpoint DNS work from AKS pods; egress rules and certificate trust are complete; no public path exists to Kafka or OpenSearch; no cloned environment can reach production endpoints |
| Kafka engineer | Cluster type limits, ACLs, prefixes, partition budget, quotas, message size, application data set cutover and failure tests are correct for Confluent Cloud |
| OpenSearch engineer | Versions match the SRS matrix; cluster settings, roles, index patterns, shard budget, watermarks, index build planning, snapshots and failure tests are correct for the chosen provider |
| Customer IT reader | A new engineer can follow each runbook step without outside help; every table is explained; nothing reads as generic or unproven |
