# Master prompt: Pega Platform 26.1.1 on Azure AKS with Confluent Cloud Kafka and managed OpenSearch

Version 2.0. Use this prompt as the complete brief for producing the customer document. Every instruction in it is mandatory unless it says "should".

---

## 1. Your role

You are writing as the delivery lead of a team that has already done this kind of implementation for other clients. The team has these members:

- a Pega Lead System Architect who has deployed Pega Platform '24.2, '25 and '26 on Kubernetes with external Kafka and SRS;
- a DevOps engineer who maintains the Pega Helm charts pipeline on AKS;
- an Azure cloud architect who owns private networking, DNS and Key Vault;
- a Kafka engineer who runs Confluent Cloud for several applications;
- an OpenSearch engineer who runs shared search clusters.

You write for the customer's IT teams: architects, platform engineers, Kafka and search operators, security, and test leads. They will build and run what you describe, so they must be able to follow every step without guessing.

## 2. What the document is about

The document covers **one subject only**: externalized Kafka and externalized search for a **fresh installation** of Pega Platform 26.1.1 on Azure AKS. In detail:

1. Kafka is provided by **Confluent Cloud**. Search is provided by a **managed OpenSearch service**, reached through the Pega **Search and Reporting Service (SRS)**.
2. Both are configured in the **Pega Helm charts** while Pega 26.1.1 is installed: the `pega` chart's `stream` and `pegasearch` sections, and the `backingservices` chart for SRS. Do not describe configuring them afterwards in the Pega UI, except for checks and settings that only exist there.
3. The document covers every environment: development, system integration test, user acceptance test, performance or pre-production, and production. Use these names unless the customer gives others, and list the assumed environment set in the scope section.
4. Non-production environments **share one Confluent Cloud cluster and one OpenSearch service**, with strict data isolation between environments, to reduce cost. Production has its own Kafka cluster and its own OpenSearch service. If you recommend a different split, explain why with evidence.

### Out of scope (state this in the document)

- Upgrading Pega 8.8 to 26.1.1, Hazelcast removal, Tomcat 10.1 and Jakarta changes, primary key preparation, and any multi-hop update path. Do not describe them.
- Moving the application, its rules or its case data from 8.8. Another workstream owns this. The document covers only what that move means for Kafka and search, as set out in section 4.
- Cassandra and Decision Data Store, Constellation, and Pega Diagnostic Center beyond the connectivity they need.
- General AKS build-out not related to Kafka or search. Cover only the networking, DNS, identity and secrets that Kafka and search depend on.

## 3. Questions the document must answer

Answer each one directly, in its own clearly titled section or table row, and cite evidence for each answer.

1. How is Confluent Cloud designed for Pega 26.1.1? Cover cluster type, networking, security, topics, partitions and sizing, per environment.
2. How is the managed OpenSearch service designed? Cover the provider choice, a version on the Pega SRS compatibility matrix, cluster settings, sizing, security and backups, per environment.
3. How exactly is each one configured in the Helm charts? Show every key used, its value per environment, and where each secret comes from.
4. How do several non-production Pega environments share one Kafka cluster and one OpenSearch service without affecting each other, and how is each environment's data kept apart? Cover naming, credentials, access control, quotas, capacity budgets, monitoring and clean-up.
5. How much does sharing save, and what risks does it add? Give a cost comparison model with the inputs the customer must supply. Do not invent prices.
6. Once 26.1.1 is configured, must Kafka topics or search indexes be migrated from Pega 8.8? Answer this as a decision (section 4).
7. How do we test it? Cover connectivity, functional checks, isolation between environments, performance, failures and recovery, and security.
8. Which failures must be tested? For each one, how is it caused, what should Pega do, how is the failure detected, and how does the system recover?
9. What are the known issues and challenges from real implementations, and how are they avoided?
10. How is it run day to day? Cover monitoring, alerts, credential and certificate rotation, capacity reviews, onboarding a new environment, and retiring an environment.

## 4. The 8.8 migration question: evidence you must use and explain

Answer the question "is there a requirement to migrate Kafka topics and search indexes from 8.8?" in a dedicated section. It needs a decision diagram and a table with one row per content type. Check each statement below against the current Pega documentation before using it. If a statement has changed, use the current text and record the change.

| Content | Expected answer | Evidence to check |
|---|---|---|
| Pega stream data: queue processor messages, delayed items, data flow partitions | **Not migrated.** Pega states that existing stream data cannot be moved to a new Kafka, because each solution stores data differently. In-flight items are finished or drained on 8.8 before its data is moved, using the Stream Migration activity if 8.8 already uses external Kafka, or by stopping intake and letting queues empty. 26.1.1 starts with empty topics that it creates itself. | Pega docs: "Switching Kafka providers while preserving Stream data"; Helm charts: `MigrationToExternalStream.md` |
| Topic names and configuration | **Not migrated.** 26.1.1 creates its own topics under its own `streamNamePattern` prefix. Only the topic settings policy, such as `max.message.bytes`, is carried over, as configuration. | Pega docs: "External Kafka in your deployment" |
| Search indexes (embedded search, legacy plug-in, or SRS on 8.8) | **Not migrated.** Indexes are built again from the 26.1.1 database. SRS indexes all searchable data after Pega connects to it, which requires a downtime period or a planned indexing window. Elasticsearch 8.x snapshots cannot be restored into OpenSearch, so snapshot copying is not an option. | Pega docs: "Connecting Pega Platform to SRS", "Rebuilding search indexes"; OpenSearch migration documentation |
| Application Kafka integrations (Kafka data sets that read or write the customer's own topics) | **Possibly in scope.** These belong to the application, not the Pega stream service. For each data set, decide whether to keep the existing topic, point it at a new cluster, or mirror it (for example with Confluent Cluster Linking, which keeps offsets), and agree the start offset. | Pega docs: Kafka data sets; Confluent Cluster Linking documentation |
| Custom search data (custom indexes, reports that depend on search) | Rebuild and verify on 26.1.1 with a count comparison. | Pega docs: index status and reindex pages |

The section must end with a short, firm statement the customer can approve, for example: "No Pega stream topic and no search index is copied from 8.8. Application Kafka topics are handled one by one as listed in Table X."

## 5. Detailed content required

### 5.1 Architecture

- **Pega's official images.** Show the 26.1.1 architecture using Pega's own images, credited to their source pages, from:
  - Pega docs, "Pega Platform Kubernetes architecture";
  - Pega docs, "External Kafka in your deployment" (Kafka use cases);
  - Pega docs, "External Search in your deployment" and the SRS pages;
  - Pega Academy topics on deployment architecture with external services and on the Search and Reporting Service.
- **New diagrams.** Draw these as clean, consistent architecture diagrams:
  1. Target architecture on Azure: AKS, Pega tiers, SRS, Application Gateway, private endpoints, Confluent Cloud network, the managed OpenSearch endpoint, Key Vault, the External Secrets Operator, and the hub firewall.
  2. Shared non-production topology: one Confluent cluster and one OpenSearch service serving four Pega environments, showing the prefix, service account, ACL, index prefix and credential boundaries.
  3. Production topology, with its dedicated services.
  4. Network and DNS flow for Confluent Private Link and the OpenSearch private endpoint, showing which DNS zone resolves which name.
  5. Secret flow: Key Vault, then the External Secrets Operator, then Kubernetes secrets, then the Pega and SRS pods.
  6. The OAuth token flow between Pega, the identity provider and SRS, including the `guid` claim check.
  7. The message path inside Pega: queue processor, topic, consumer group, partition, and the batch tier.
- **Decision diagrams.** Include one for each of:
  - the Confluent cluster type;
  - shared or dedicated services per environment;
  - one SRS per environment or one shared SRS;
  - the OpenSearch provider;
  - Kafka authentication;
  - whether to migrate 8.8 content;
  - the treatment of application Kafka data sets;
  - troubleshooting Kafka;
  - troubleshooting search.

### 5.2 Confluent Cloud design

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
  - Naming pattern per environment, for example `pega-dev-{stream.name}` and `pega-sit-{stream.name}`.
  - Replication factor and `max.message.bytes`.
  - Who creates topics: Pega through the admin client, or pre-created topics if policy forbids creation rights.
  - The topics Pega '25 and later need for clustering after Hazelcast removal (verify the list).
- **Partition budget.** Give a method that measures partitions per environment after the first full start, then adds headroom. Show a worked table with placeholders for the measured numbers, and compare the total with the cluster limit.
- **Quotas and noisy neighbours.** Cover client quotas per service account where the cluster type supports them (verify availability), producer and consumer limits, and what to do if one environment's load test affects the others.

### 5.3 Managed OpenSearch design

- **Provider options on Azure.** Azure has no first-party managed OpenSearch, so compare third-party managed providers that run on Azure with self-managed OpenSearch on AKS. Assess each on:
  - an OpenSearch version on the SRS matrix;
  - private connectivity;
  - settings control (`action.auto_create_index`, `action.destructive_requires_name`);
  - fine-grained access control;
  - snapshots;
  - support terms.

  Do not name prices.
- **SRS compatibility.** Give the SRS image and OpenSearch versions certified for 26.1.1, with the image name `search-n-reporting-service-os`. Where the Pega documentation and the Helm chart README disagree, record the conflict and follow the stricter source.
- **Cluster settings and sizing.** Give the required cluster settings with the exact API call. Cover sizing (Pega's published sizing tables), shards and replicas per index, the shard budget per node, and disk watermarks.
- **Isolation in the shared non-production service.**
  - A distinct `customerDeploymentId` per environment, which becomes the index prefix.
  - One SRS per environment (recommended for isolation) or one shared SRS. Compare credentials, blast radius, upgrades and cost.
  - An OpenSearch role per environment restricted to that environment's index pattern, if SRS works with index-scoped permissions. Verify whether SRS needs cluster-level privileges and state the result.
  - Clean-up of indexes when an environment is rebuilt or retired.
- **Backups and restore.** Explain that indexes can always be rebuilt from the Pega database. Snapshots shorten recovery but are optional, so state the recovery time for each choice.

### 5.4 Helm configuration, per environment

- **Every key**, in one table per chart:
  - for the `pega` chart: `global.customerDeploymentId`, the `stream.*` keys, `pegasearch.*` (including `srsAuth` and `srsMTLS`), `external_secret_name`, the tier settings that matter for Kafka consumers, and the `hazelcast` keys left at their '26 defaults;
  - for the `backingservices` chart: `srsRuntime`, `srsStorage` and `networkPolicy`.

  Columns: key, meaning, DEV, SIT, UAT, PERF, PROD, and source.
- **Complete, valid YAML** values files for one non-production environment and for production. Check every key against the Helm chart README of the chart version used, and state that version.
- **The secret inventory.** Give the exact key names the charts require (`STREAM_TRUSTSTORE_PASSWORD`, `STREAM_KEYSTORE_PASSWORD`, `STREAM_JAAS_CONFIG`, `SRS_OAUTH_PRIVATE_KEY`, and the SRS storage `username` and `password`), the Key Vault names, and the External Secrets Operator manifests.
- **Install order and checks.** Pega's install action and its order relative to SRS: network, DNS, secrets, Confluent, OpenSearch, SRS, then Pega install-deploy. Include a check after each step.

### 5.5 Testing

- **Test stages.** Cover connectivity, configuration, functional, isolation, performance, resilience, security and operational acceptance. For each, give the entry criteria, the environment, the owner and the evidence produced.
- **Isolation tests.** Prove that environment A cannot read, write or delete environment B's topics, consumer groups or indexes, using negative tests with A's credentials.
- **Failure scenario catalogue**, at least 20 rows. Columns: ID, scenario, how to cause it safely, expected Pega behaviour, detection (log message, alert, landing page), recovery, and pass criteria. Include at least:
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
    - a wrong `customerDeploymentId` is deployed by mistake.
- **Exact checks.** For each check, give the command or screen: the Stream landing page, queue processor status, the search landing page, the Confluent CLI, `kcat`, the OpenSearch `_cluster/health`, `_cat/indices` and `_cluster/settings` APIs, and `kubectl`.

### 5.6 Known issues and challenges

Write these as experience-based guidance: the symptom, the cause, how to prevent it, and how to fix it. Include at least:

- **Kafka and Confluent:**
  - Kafka clients reach the bootstrap server but fail on broker connections because broker names resolve to public IPs (Private Link DNS).
  - Too many partitions from many queue processors on a shared cluster.
  - The Confluent topic message size default is lower than Pega's requirement.
  - A JAAS string is stored with the wrong quoting.
  - A secret is changed but pods were not restarted.
  - Topic creation is denied because the policy forbids CREATE.
  - From '25, Pega uses Kafka for cluster communication after Hazelcast removal, so a Kafka outage affects more than queue processing. Verify this and explain the consequence.
- **OpenSearch and SRS:**
  - Indexes are auto-created with the wrong settings, or index auto-creation is blocked.
  - OAuth claims from the chosen identity provider do not match what SRS checks. For example, Microsoft Entra ID application tokens carry `roles`, not `scp`, and no `guid`. Verify this and give the fix.
  - An SRS image version is not on the matrix for the OpenSearch version.
  - The time for a full reindex is underestimated.
  - Indexes are orphaned after an environment is rebuilt with a new `customerDeploymentId`.
- **Process:** a non-production data refresh from production. Any copied data must be re-indexed under the target environment's own ID, and production credentials must never be used.

### 5.7 Operations

- A monitoring table: the signal, its source (Confluent Metrics API, provider metrics, SRS logs, Pega alerts), the threshold and the response.
- Routine tasks with frequency and owner: API key rotation, certificate renewal, partition and shard capacity review, SRS image updates, OpenSearch version updates, and cost review.
- Onboarding a new non-production environment onto the shared services, as a numbered checklist.
- Retiring an environment, as a checklist: delete the ACLs, service account, topics, consumer groups, indexes, OpenSearch role and secrets, and record evidence.
- A RACI between the customer platform team, the Kafka team, the search team, the Pega team, Confluent, and the OpenSearch provider.

### 5.8 Risks, open decisions, assumptions

- A risk register with likelihood, impact, mitigation and owner.
- Open decisions, each with options, a recommended answer, an owner and the date by which it is needed: Confluent cluster types, the OpenSearch provider, SRS per environment or shared, the identity provider, the environment list, and the quota approach.
- Assumptions, each with the check that would prove it wrong.

## 6. Evidence rules

1. **Every product statement must cite a source** in square brackets, such as [R7], resolving to a numbered reference list with full URLs. Use, in order of authority:
   - Pega documentation for Pega Platform '26;
   - the Pega Helm charts GitHub repository (state the chart version);
   - Pega Academy;
   - Confluent Cloud documentation;
   - OpenSearch documentation and the chosen provider's documentation;
   - Microsoft Learn.
2. **Read each page before citing it**, and record the date it was read.
3. **If no source settles a point**, say so plainly and turn it into a test in the test plan, or into an open decision. Never fill the gap with an assumption written as fact.
4. **Record conflicts between sources** in a reconciliation table: the topic, what each source says, and the decision taken.
5. **Do not state version numbers, limits or defaults from memory.** Copy them from the cited page.
6. **Pega and third-party images** must carry a source line under the figure. An appendix lists every image with its page and a note that reuse rights must be confirmed before external distribution.

## 7. Writing rules

- **Plain English.** Short sentences in the active voice, one idea per sentence. Write the way an experienced engineer explains a design to a colleague.
- **Explain every table** in the text before or after it: what it shows and what the reader should do with it. Number and caption every table and figure, and refer to them by number.
- **Use precise verbs and real nouns**: "set", "create", "check", "restart", "the batch tier", "the service account".
- **Do not use these words or patterns:**
  - leverage, seamless, robust, comprehensive, cutting-edge, state-of-the-art, holistic, synergy, empower, unlock, elevate, streamline, delve, navigate (except for UI navigation), landscape (except Pega's sizing column name), journey, game-changer, best-in-class, world-class, crucial, vital, pivotal, paramount;
  - "it is important to note", "in today's", "in conclusion", "overall", "furthermore", "moreover";
  - em dashes, rhetorical questions, exclamation marks, and marketing claims.
- **Do not write sentences that say nothing**, such as "This section describes...". Start with the fact.
- **Keep naming consistent.** Use one name per concept and the same environment codes, IDs and prefixes everywhere.
- **Use requirement words carefully.** "Must" is for vendor requirements and fixed decisions only. "Should" is for recommendations.
- **Use angle brackets for environment-specific values** in commands and YAML, for example `<bootstrap-host>`. List each one in the configuration inventory appendix.

## 8. Document structure and format

Produce a Word document (DOCX) with an A4 page, a header with the short title, and a footer reading "Customer Confidential | Page X of Y". It must have:

1. **Front matter:**
   - a cover page;
   - document control: version, status, date, evidence cut-off date and owner;
   - revision history;
   - approvals with signature rows;
   - a table of contents with page numbers;
   - a list of figures;
   - a list of tables.
2. **Executive summary:** the design in one page, the cost-sharing approach, the answer to the 8.8 migration question, and the decisions needed.
3. Scope, assumptions and reading guide by role.
4. Evidence baseline: versions and support facts with sources.
5. Architecture (5.1).
6. Shared and dedicated service model, with isolation and cost (5.2, 5.3, and question 5).
7. Confluent Cloud design and configuration (5.2).
8. Managed OpenSearch and SRS design and configuration (5.3).
9. Helm configuration per environment (5.4).
10. Secrets, certificates and identity.
11. Deployment runbook per environment, with numbered steps, owner, check and evidence.
12. The 8.8 content question: decision and treatment (section 4).
13. Test strategy and failure scenarios (5.5).
14. Known issues and challenges (5.6).
15. Troubleshooting, with decision trees and symptom tables.
16. Operations, onboarding and retirement (5.7).
17. Risks, open decisions, assumptions and source reconciliation (5.8, 6.4).
18. **Appendices:**
    - A. Configuration inventory per environment.
    - B. Complete Helm values files.
    - C. Command reference.
    - D. Evidence and test record templates.
    - E. Glossary.
    - F. References with links.
    - G. Image sources and attribution.

Expected size: 70 to 100 pages. Diagrams must be legible when printed on A4. Code blocks must not wrap.

## 9. Acceptance checks before release

The document is complete only when every check passes. Report the result of each check with the document.

1. Every [Rn] resolves to the reference list, and every reference is cited at least once.
2. Every section, figure and table cross-reference points to the right target.
3. No banned words or patterns (section 7), and no placeholder text other than angle-bracket values listed in Appendix A.
4. Every YAML block parses, and every Helm key exists in the chart version stated.
5. Every command has been checked for correct syntax for the tool version stated.
6. Every question in section 3 has a findable answer. Give a traceability table from question to section.
7. Every failure scenario has its cause, expected behaviour, detection, recovery and pass criteria filled in.
8. Every Pega or third-party figure has a source line.
9. Five reviewer checklists (section 10) are completed, and their findings are fixed or logged.

## 10. Expert review before release

Review the finished document once from each viewpoint below. Fix what you find, and list the findings and fixes in a short review log, which is kept out of the customer copy.

| Reviewer | Must confirm |
|---|---|
| Pega Lead System Architect | Stream and search behaviour matches Pega '26 documentation; queue processor, data flow and index status checks are correct; the 8.8 content decision is correct; `customerDeploymentId` handling is safe |
| DevOps engineer | Helm keys and YAML are valid for the stated chart version; the install order works; secrets never appear in values files; the pipeline steps are repeatable per environment |
| Azure cloud architect | Private Link and private endpoint DNS work from AKS pods; egress rules and certificate trust are complete; no public path exists to Kafka or OpenSearch |
| Kafka engineer | Cluster type limits, ACLs, prefixes, partition budget, quotas, message size and failure tests are correct for Confluent Cloud |
| OpenSearch engineer | Versions match the SRS matrix; cluster settings, roles, index patterns, shard budget, watermarks, snapshot approach and failure tests are correct for the chosen provider |
| Customer IT reader | A new engineer can follow each runbook step without outside help; every table is explained; nothing reads as generic or unproven |
