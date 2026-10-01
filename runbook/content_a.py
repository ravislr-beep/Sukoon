"""Front matter and Sections 1 to 6."""
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx_lib import NAVY, GREY, _fix_grid

GEN = "img/generated/"
PUB = "img/public/"
OWN = "Prepared for this implementation. Not a Pega-published diagram."


def cover(b, meta):
    d = b.doc
    for _ in range(5):
        d.add_paragraph()
    p = d.add_paragraph()
    r = p.add_run("CUSTOMER ENGINEERING RUNBOOK")
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = GREY
    p = d.add_paragraph()
    r = p.add_run("Pega Platform 26.1.1 on Azure Kubernetes Service")
    r.font.size = Pt(26)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p = d.add_paragraph()
    r = p.add_run("Externalized Kafka (Confluent Cloud) and Search (SRS with Elasticsearch or OpenSearch)")
    r.font.size = Pt(15)
    r.font.color.rgb = NAVY
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("Design, deployment, configuration and migration from Pega Platform 8.8, "
                  "including Kafka topic and search index migration requirements, validation, strategy and execution")
    r.font.size = Pt(12)
    r.font.color.rgb = GREY
    for _ in range(6):
        d.add_paragraph()
    rows = [
        ("Document version", meta["version"]),
        ("Status", meta["status"]),
        ("Issue date", meta["date"]),
        ("Classification", "Customer Confidential"),
        ("Target release", "Pega Platform 26.1.1 (Pega Platform '26), client-managed cloud on Azure AKS"),
        ("Source release", "Pega Platform 8.8"),
    ]
    t = d.add_table(rows=0, cols=2)
    for k, v in rows:
        c = t.add_row().cells
        c[0].width, c[1].width = Cm(4.5), Cm(11.5)
        r = c[0].paragraphs[0].add_run(k)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = NAVY
        r = c[1].paragraphs[0].add_run(v)
        r.font.size = Pt(10)
    _fix_grid(t, [4.5, 11.5])


def document_control(b, meta):
    p = b.doc.add_paragraph(style="Front Heading")
    p.paragraph_format.page_break_before = True
    p.add_run("Document control")
    b.table(["Item", "Detail"], [
        ["Title", "Pega Platform 26.1.1 on Azure AKS: externalized Kafka and search. Design, deployment, configuration and migration runbook"],
        ["Version", meta["version"]],
        ["Status", meta["status"]],
        ["Issue date", meta["date"]],
        ["Evidence cut-off", "Vendor documentation was read on 1 October 2026. Section 3 lists the version facts used and Appendix F lists every source."],
        ["Supersedes", "The draft integrated customer engineering runbook (sections 1 to 30, decisions D-01 to D-12, open decisions OD-01 to OD-15). This document replaces its Kafka, search and upgrade content and renumbers the open decisions (Section 22)."],
        ["Owner", "Customer platform engineering lead"],
        ["Review cycle", "Before each rehearsal and before each production release (Section 13)"],
    ], widths=[3.5, 13], first_col_bold=True, size=9.5)
    p = b.doc.add_paragraph(style="Front Heading")
    p.paragraph_format.space_before = Pt(14)
    p.add_run("Revision history")
    b.table(["Version", "Date", "Change", "Author"], [
        ["0.1 to 0.9", "2026", "Draft integrated runbook (customer engineering).", "Customer engineering"],
        ["1.0", meta["date"], "Rewritten and evidence-checked runbook. Adds the 8.8 upgrade path, Kafka topic and search index migration, decision diagrams, validation matrices and appendices.", "Implementation team"],
    ], widths=[2, 2.5, 9, 3])
    p = b.doc.add_paragraph(style="Front Heading")
    p.paragraph_format.space_before = Pt(14)
    p.add_run("Approvals")
    b.p("Approval confirms that the approver has reviewed the sections relevant to the role and accepts the recommendations and open decisions as stated.")
    b.table(["Role", "Name", "Signature", "Date"], [
        ["Customer business owner", "", "", ""],
        ["Customer enterprise architect", "", "", ""],
        ["Customer security architect", "", "", ""],
        ["Customer platform engineering lead", "", "", ""],
        ["Pega Lead System Architect", "", "", ""],
        ["Kafka and search engineering lead", "", "", ""],
    ], widths=[5.5, 4.5, 4, 2.6], zebra=False)


def s1_exec(b):
    b.h1("Executive summary")
    b.h2("Purpose")
    b.p("This runbook explains how to build Pega Platform 26.1.1 on Azure Kubernetes Service (AKS) with Kafka provided by "
        "Confluent Cloud and search provided by the Pega Search and Reporting Service (SRS) backed by an Elasticsearch or "
        "OpenSearch cluster. It also explains how to move the current Pega Platform 8.8 system to that platform, with particular "
        "attention to two questions the customer asked: what happens to Kafka topics, and what happens to search indexes. "
        "For each, the runbook states the requirement, the validation needed, the strategy chosen and the steps to execute it.")
    b.h2("Facts that shape the plan")
    b.p("The plan follows from six published facts. Each one is taken from vendor documentation and referenced.")
    b.table(["#", "Fact", "Consequence for this programme", "Source"], [
        ["1", "From Pega Platform '24.2, embedded Kafka, Elasticsearch and Cassandra are not supported. Kafka and search must be external.",
         "Pega 26.1.1 needs Confluent Cloud and SRS in place before it can run.", "[R2]"],
        ["2", "From Pega Platform '25, only containerized deployments are supported, on Tomcat 10.1 (Jakarta EE).",
         "Custom JARs and CodeSets that use Java EE (javax) packages must be rebuilt for Jakarta EE.", "[R2, R3]"],
        ["3", "Hazelcast is removed in Pega Platform '25. It must be removed before updating to '25 or later. The removal tooling exists only in patches 23.1.4, 23.1.5, 24.1.3, 24.1.4, 24.2.2, 24.2.3 and later.",
         "Pega 8.8 cannot be updated directly to 26.1.1. An intermediate (bridge) release is needed.", "[R5, R9]"],
        ["4", "All tables must have primary keys before an update to '25 or later.",
         "Run the primaryKeyUtility on 8.8 in dry-run mode early and fix gaps.", "[R3, R12]"],
        ["5", "Stream data stored in Kafka cannot be moved to a new Kafka provider. Pega provides a Stream Migration activity (8.7 and later) that drains queues before the switch.",
         "Kafka topics are not copied. They are drained on the source and created empty on Confluent.", "[R15]"],
        ["6", "After Pega connects to SRS, SRS indexes all searchable data from the database. This needs a downtime period.",
         "Search indexes are rebuilt from the database, not copied. The build time is measured in rehearsal.", "[R17]"],
    ], caption="Published facts that shape the plan", widths=[0.7, 6.3, 6.6, 1.6], size=9)
    b.h2("Recommended approach")
    b.p("The recommended path has three production releases. Each release changes one class of thing, so a failure has one "
        "likely cause and a simple rollback.")
    b.figure(GEN + "fig_upgrade_path.png", "Recommended three-release path from Pega 8.8 to Pega 26.1.1", OWN, width_cm=11.5, label="upgrade_path")
    b.table(["Release", "What changes", "What does not change", "Main evidence of success"], [
        ["Release 1: externalize on 8.8", "8.8 switches from its current stream service to Confluent Cloud, and from its current search to SRS. Full index build.",
         "Pega software version, servers, database.", "Stream landing page shows Provider ExternalKafka and Status NORMAL [R15]. Index status complete for all classes [R21]."],
        ["Release 2: platform move", "Database copied to Azure and updated to the bridge release (latest '24.1 patch, 24.1.4 or later). Pega runs on AKS. Hazelcast removed.",
         "Confluent cluster and search cluster (new topic prefix and new index prefix on them).", "Hazelcast decommission APIs report success [R8]. Smoke and regression tests pass."],
        ["Release 3: release update", "Zero-downtime update from the bridge release to 26.1.1.",
         "AKS cluster, Confluent topics, SRS indexes.", "Installer job completes. Stream and search checks pass on 26.1.1."],
    ], caption="The three releases", widths=[3.2, 5.5, 3.6, 4.3], size=9)
    b.p("Pega's own published sequence for clients on older releases is the same in substance: update to the latest '24.1 patch, "
        "externalize Kafka, search and (where used) Cassandra, remove Hazelcast, move to containers, then update to '25 or later [R2]. "
        "Release 1 moves externalization ahead of the software update because Pega advises migrating from embedded stream "
        "to external Kafka before a software update, and not changing the Pega version during a stream provider switch [R30, R33].")
    b.h2("Decisions the customer needs to take")
    b.p("The following open decisions affect cost, timeline or security and need an owner and a date. Section 22 lists all of them.")
    b.table(["ID", "Decision", "Recommended answer"], [
        ["OD-02", "Bridge release patch", "Latest '24.1 patch (24.1.4 or later), confirmed with Pega Support."],
        ["OD-03", "Three releases or a combined Release 1 and 2", "Three releases."],
        ["OD-04", "Search provider", "Managed OpenSearch from an Azure-hosted provider, or Elastic Cloud on Azure if Elastic licensing is accepted. Both meet the SRS matrix [R16]."],
        ["OD-05", "Confluent Cloud cluster type", "Enterprise with Private Link, or Dedicated if the partition budget or networking needs exceed Enterprise limits [R37]."],
        ["OD-06", "Kafka authentication", "SASL_SSL with PLAIN (Confluent API key in Key Vault) as the documented Helm path [R28]."],
        ["OD-16", "Identity provider for Pega-to-SRS OAuth", "Choose a provider that can issue the scope and guid claims SRS needs; prove it in the first environment."],
    ], caption="Open decisions that need an early answer", widths=[1.6, 5, 10], size=9)
    b.h2("Readiness statement")
    b.p("This document is ready for customer review and approval as a design and runbook. It does not replace the rehearsals it "
        "prescribes. Durations for draining, database copy, update and index build depend on data volumes and must come from the "
        "staging rehearsal (Section 16), not from estimates. Where vendor sources disagree, the conflict is recorded in Section 23 "
        "with the action taken.")


def s2_scope(b):
    b.h1("Scope and how to use this document")
    b.h2("Scope")
    b.table(["In scope", "Out of scope"], [
        [["Pega Platform 26.1.1 on AKS using the Pega Helm charts (pega and backingservices).",
          "Confluent Cloud as the Pega stream service: cluster type, networking, security, topics and Helm configuration.",
          "SRS with Elasticsearch or OpenSearch: provider choice, sizing, security and Helm configuration.",
          "Upgrade path from Pega 8.8, including Hazelcast removal, Tomcat 10.1 and primary key prerequisites.",
          "Kafka topic migration and search index migration: requirements, validation, strategy and execution.",
          "Cutover, rollback, testing, troubleshooting, observability and operations for these components."],
         ["Pega application design changes and functional regression content (owned by the application team).",
          "Cassandra and Decision Data Store. Cassandra is required only for Pega Customer Decision Hub and Pega Process AI [R22]. If either is licensed, a separate plan is needed.",
          "Constellation UI service and Pega Diagnostic Center onboarding beyond connectivity.",
          "Database engine migration. The database engine and version must be on the 26.1.1 Platform Support Guide [R1].",
          "Commercial terms with Confluent, Elastic or OpenSearch providers."]],
    ], caption="Scope of this document", widths=[8.3, 8.3], size=9.5, zebra=False)
    b.h2("Audience and reading guide")
    b.table(["Reader", "Read first", "Then"], [
        ["Business owner, programme manager", "Section 1, Section 10.3, Section 14, Section 21, Section 22", "Section 15"],
        ["Enterprise and security architects", "Sections 4, 5, 7.5, 8.8, 9", "Sections 21 to 23"],
        ["Pega Lead System Architect", "Sections 10, 11, 12", "Sections 14 to 17"],
        ["Platform, Kafka and search engineers", "Sections 6 to 9 and 13", "Sections 17, 18, Appendices B and D"],
        ["Test lead", "Section 16", "Validation matrices in Sections 11.5 and 12.5"],
    ], caption="Reading guide by role", widths=[5, 6.5, 5.1], size=9.5)
    b.h2("Conventions")
    b.bullets([
        "**Must** marks a vendor requirement or a fixed customer decision. **Should** marks a recommendation that can be changed through the decision process in Section 5.",
        "Values in angle brackets, for example `<env>` or `<bootstrap-host>`, are environment-specific. Each one is listed in the configuration inventory in Appendix A and recorded before deployment.",
        "References in square brackets, for example [R13], point to the numbered sources in Appendix F.",
        "\"Bridge release\" means the intermediate Pega release between 8.8 and 26.1.1. \"Release 1\", \"Release 2\" and \"Release 3\" mean the three production changes in {ref:fig_upgrade_path}.",
        "\"Search cluster\" means the Elasticsearch or OpenSearch cluster that stores SRS indexes. \"Stream\" means the Pega stream service, which uses Kafka.",
        "Figures marked \"Prepared for this implementation\" were drawn for this document. Figures from Pega, Pega Academy, Confluent and OpenSearch are reproduced with attribution (Appendix G).",
    ])
    b.h2("How the evidence was gathered")
    b.p("Every statement about product behavior comes from one of these sources, in this order of authority:")
    b.steps([
        "Pega documentation for Pega Platform '26 (docs.pega.com), and for '25 or '24.1 where the topic belongs to that release (for example, Hazelcast removal).",
        "The Pega Helm charts repository on GitHub (chart version 4.13.0) for configuration keys and defaults.",
        "Pega Academy for architecture illustrations and deployment patterns.",
        "Confluent, OpenSearch, Microsoft and Apache Kafka documentation for their own products.",
    ])
    b.p("Where two sources disagree, the higher one is followed and the conflict is logged in Section 23. Where no source "
        "settles a point, the document says so and turns it into a validation step or an open decision.")


def s3_evidence(b):
    b.h1("Evidence baseline: versions and support facts")
    b.p("The table records the facts this design depends on, as published on the evidence cut-off date. Re-check them before "
        "each release, because vendors update these pages.")
    b.table(["Topic", "Fact", "Source"], [
        ["Target release", "Pega Platform '26; the Platform Support Guide covers 26.1.x.", "[R1]"],
        ["Kubernetes", "AKS is a supported environment. x86-64 nodes only (no ARM). At least two worker nodes with 32 GB RAM. Database in the same region as the worker nodes. Tomcat must be the one in the Pega image.", "[R22]"],
        ["Helm", "Helm 3.0 or later. Pega Helm charts 4.13.0 used for this design.", "[R22, R28]"],
        ["Kafka requirement", "\"All Queue Processors and Job Schedulers in Pega Platform require Kafka.\" Without it, Pega Platform is not fully functional.", "[R13]"],
        ["Kafka client", "Pega '26 ships the Kafka client library 4.0.0, backward compatible with 3.9.2, and supports Kafka server 4.0.0.", "[R3, R22]"],
        ["Kafka settings", "message.max.bytes 5000000; replica.fetch.max.bytes 5000100; replica.fetch.response.max.bytes 5000100; unclean.leader.election.enable false; auto.create.topics.enable false.", "[R13]"],
        ["Kafka security", "Generic Kafka settings only; vendor-specific features such as IAM roles are not supported. Mechanisms: SASL using JAAS, SASL/OAUTHBEARER, SASL/PLAIN, SASL/SCRAM.", "[R13]"],
        ["Kafka ACLs", "TOPIC and GROUP on the streamNamePattern prefix (ALL, PREFIXED); TRANSACTIONAL_ID * (READ/WRITE, LITERAL); CLUSTER IDEMPOTENT_WRITE (LITERAL).", "[R13]"],
        ["Confluent version", "If Confluent is the provider, use 5.4.x or later, compatible with the supported Kafka version.", "[R13]"],
        ["Stream migration", "Stream Migration activity available from 8.7. Drains RUNNING queue processors and data flows only. Does not transfer stored data.", "[R15]"],
        ["Search", "SRS replaces embedded search and the legacy plug-in (deprecated in 8.8, removed in '24.2).", "[R16]"],
        ["SRS matrix", "Pega 8.6 and later: SRS 1.44.3 or later. Elasticsearch with authentication: 7.17.9, 7.17.29, 8.10.3, 8.15.1, 8.15.5, 8.18.2, 8.18.3, 8.19.11. OpenSearch image: AWS Elasticsearch 7.10, OpenSearch 1.3, 2.15, 2.19.", "[R16]"],
        ["Search settings", "Index auto-creation off (SRS sets it if its user has the manage cluster privilege); action.destructive_requires_name false.", "[R16]"],
        ["Index build", "After connecting to SRS, SRS indexes all searchable data; this requires downtime.", "[R17]"],
        ["Hazelcast", "Removed in '25. Remove before updating. Removal needs 23.1.4, 24.1.3, 24.2.2 or later patches.", "[R5, R9]"],
        ["Hazelcast prerequisites", "About 100 additional Kafka partitions per environment; database CPU buffer of at least 10 %; Kafka CPU buffer of at least 15 % below alert thresholds.", "[R6]"],
        ["Tomcat", "Tomcat 10.1 only from '25. Rules referencing Java EE convert automatically; custom CodeSets and JARs must be updated.", "[R3, R11]"],
        ["Primary keys", "All tables need primary keys before updating to '25 or later (primaryKeyUtility).", "[R3, R12]"],
        ["Queue processing", "'26 moves to partitioned, multi-threaded processing. Remove DSS delayeditems/dataflowbased/threadspernode (PEGA0179).", "[R3]"],
        ["System Pulse", "Set SystemPulse_SystemPulseTopicName to 6 partitions if dynamic topic creation is restricted.", "[R3]"],
        ["Zero-downtime update", "Helm upgradeType zero-downtime, for updates from 8.4.2 and later.", "[R28, R33]"],
    ], caption="Version and support facts used in this design", widths=[2.8, 12, 1.8], size=8.5)


def s4_arch(b):
    b.h1("Current state and target architecture")
    b.h2("Source estate assessment")
    b.p("Several choices in this runbook depend on facts about the 8.8 estate. Collect them first and record the answers in "
        "Appendix A. Each row names the check and why it matters.")
    b.table(["Item", "How to check", "Why it matters"], [
        ["Exact 8.8 patch", "Dev Studio: About Pega Platform; or the installer log.", "Sets the starting point of the update path and any hotfix prerequisites."],
        ["Deployment type", "Infrastructure inventory: VMs or Kubernetes.", "VMs are not supported from '25 [R2]; affects how Release 1 is configured."],
        ["Stream mode", "Configure > Decisioning > Infrastructure > Services > Stream. Provider shows embedded stream nodes or ExternalKafka.", "Decides how Release 1 drains and switches the stream (Section 11.4)."],
        ["Search mode", "Search landing page and prconfig or Helm values: embedded, legacy plug-in, or SRS.", "Embedded and plug-in data cannot be reused; a full SRS index build is needed (Section 12)."],
        ["Hazelcast mode", "Helm values (hazelcast.enabled, hazelcast.clusteringServiceEnabled) or prconfig.", "Embedded Hazelcast or the Clustering Service changes the removal steps [R8]."],
        ["Database engine and version", "DBA inventory.", "Must be on the 26.1.1 Platform Support Guide [R1]."],
        ["Custom JARs and CodeSets", "Pega Update Tools and the Tomcat 10.1 checks [R11].", "Java EE packages must move to Jakarta EE for '25 and later."],
        ["Tables without primary keys", "primaryKeyUtility in dry-run mode [R12].", "Blocks the update to '25 and later."],
        ["Custom queue processors and DSS", "Records > SysAdmin > Dynamic System Settings; queue processor rules.", "PEGA0179 change in '26; DSS delayeditems/dataflowbased/threadspernode must be removed [R3]."],
        ["Kafka data sets", "Records > Data Model > Data Set, type Kafka; Kafka configuration instances.", "Application Kafka integrations are separate from the stream service and are handled in Section 11.4."],
        ["Searchable data volume", "Search landing page per class; database row counts of indexed classes.", "Drives search cluster sizing (Section 8.4) and index build time."],
        ["Queue backlog", "Admin Studio > Queue processors: Ready to process, Broken.", "Large backlogs lengthen the drain step; broken items must be resolved or accepted before the drain."],
        ["Licensed Pega applications", "Application stack in Dev Studio.", "Customer Decision Hub or Process AI bring Cassandra and Kafka data set needs [R13, R22]."],
    ], caption="Source estate assessment checklist", widths=[3.4, 6.1, 7.1], size=8.5)
    b.h2("Pega reference architecture for '26")
    b.p("Pega's published Kubernetes architecture for '26 has three layers: the Pega application namespace (web and batch "
        "deployments plus an installer job), backing services that Pega provides (SRS and Constellation), and technologies the "
        "client provides (Elasticsearch or OpenSearch, Kafka, Cassandra for CDH only, and the database) [R23]. Hazelcast does not "
        "appear, because '25 removed it.")
    b.figure(PUB + "pega_docs_pega-platform-architecture.png",
             "Pega Platform Kubernetes architecture for '26",
             "Source: Pega Documentation, \"Pega Platform Kubernetes architecture\" [R23]. © Pegasystems Inc. Reproduced with attribution. The database shown is an example; any database on the Platform Support Guide can be used.",
             width_cm=14)
    b.p("Pega Academy describes the same move from embedded to external services. Before externalization, Kafka, Cassandra and "
        "Elasticsearch ran inside the Pega cluster. After it, they are separate services the client operates, and Pega reaches "
        "search only through SRS [R35].")
    b.figure(PUB + "pega_academy_external_services.png",
             "Externalized services in a Pega deployment",
             "Source: Pega Academy, \"Deployment architecture with external services\" [R35]. © Pegasystems Inc. Reproduced with attribution.",
             width_cm=13)
    b.h2("Target architecture on Azure")
    b.p("{ref:fig_target} shows the target. Pega web and batch tiers, the installer job and SRS run in a private AKS cluster in the "
        "customer subscription. Every managed service is reached through a private endpoint in a dedicated subnet. Users reach Pega "
        "through Azure Application Gateway with Web Application Firewall. Secrets come from Azure Key Vault through the External "
        "Secrets Operator. Outbound traffic leaves through the hub firewall.")
    b.figure(GEN + "fig_target_architecture.png", "Target architecture on Azure AKS", OWN, width_cm=16.5, label="target")
    b.table(["Component", "Role", "Design choice", "Reference"], [
        ["Application Gateway WAF v2 and ingress controller", "Public entry point; TLS termination and re-encryption to the web tier", "Backend TLS to the web pods (tier.service.tls); request timeout set with appgw.ingress.kubernetes.io/request-timeout", "[R28]"],
        ["Web tier", "User and API traffic (nodeType WebUser)", "HPA on CPU; PDB enabled", "[R28]"],
        ["Batch tier", "Background processing, search indexing, batch, real-time and custom node types", "No ingress; sized for queue processor load", "[R23, R28]"],
        ["Installer job", "Install and update the database schemas", "Runs only during install or update", "[R28]"],
        ["SRS", "Search and Reporting Service between Pega and the search cluster", "Three replicas, no ingress, network policy enabled, OAuth enabled", "[R16, R29]"],
        ["External Secrets Operator", "Synchronizes Key Vault secrets into Kubernetes secrets", "Workload identity to Key Vault", "[R28, R47]"],
        ["Confluent Cloud", "Kafka for the Pega stream service", "Enterprise or Dedicated, private connectivity, RF 3", "[R13, R37, R38]"],
        ["Search cluster", "Elasticsearch or OpenSearch storage for SRS", "Three cluster-manager and three or more data nodes; private connectivity", "[R16]"],
        ["Pega database", "Rules and data schemas", "Same region as AKS; private endpoint; TLS", "[R22]"],
        ["Key Vault, Container Registry", "Secrets and certificates; Pega images", "Private endpoints; images pulled from Pega and scanned", "[R28]"],
    ], caption="Target architecture components", widths=[3.4, 4.2, 6.6, 2.4], size=8.5)
    b.h2("Logical data flows")
    b.p("{ref:fig_flows} shows the five flows that matter for Kafka and search. Flow 1 is the user request. Flow 2 is queue processing: "
        "producers on any tier write to Kafka topics and the batch tier consumes them. Flow 3 is search: the batch tier indexes "
        "changed records through SRS, and the web tier sends queries through SRS. Flows 4 and 5 are administration and telemetry.")
    b.figure(GEN + "fig_logical_flows.png", "Logical flows between Pega, Kafka, SRS and the search cluster", OWN, width_cm=10, label="flows")
    b.h2("Tiers, namespaces and node pools")
    b.table(["Namespace", "Workload", "Chart", "Node pool", "Notes"], [
        ["`pega-<env>`", "Web tier, batch tier, installer job", "pega", "pega (user pool, 3 zones)", "Pega namespaces in Pega's architecture are named mypega in examples [R23]."],
        ["`srs-<env>`", "SRS deployment and service", "backingservices", "srs (user pool) or shared user pool", "SRS can serve more than one Pega environment through customerDeploymentId isolation [R16]."],
        ["`platform-ops`", "External Secrets Operator, monitoring agents", "vendor charts", "system or user pool", "Kept separate from Pega to limit RBAC scope."],
        ["`kube-system`", "AKS system components", "AKS managed", "system pool", "No Pega workloads."],
    ], caption="Namespaces, charts and node pools", widths=[2.6, 3.6, 2.4, 3.2, 4.8], size=8.5)


def s5_decisions(b):
    b.h1("Decision framework")
    b.h2("Fixed customer decisions carried forward")
    b.p("The draft runbook recorded twelve fixed decisions (D-01 to D-12). Three of them directly constrain the Kafka and search design "
        "and are applied throughout this document.")
    b.table(["ID", "Decision", "Effect in this document"], [
        ["D-07", "Azure Event Hubs is not used as the Pega Kafka service.", "Confluent Cloud is the Kafka provider. This also matches Pega's statement that vendor-specific security features are not supported [R13]."],
        ["D-08", "No Azure-managed Elasticsearch service.", "The search provider is chosen from the options in Section 8.3 (OD-04)."],
        ["D-09", "No plain-text secrets in Helm values.", "All passwords, JAAS strings and keys are delivered through external_secret_name and the External Secrets Operator (Section 9)."],
    ], caption="Fixed customer decisions that constrain Kafka and search", widths=[1.5, 6, 9.1], size=9)
    b.h2("Architecture decisions made in this document")
    b.table(["ID", "Decision", "Choice", "Reason", "Source"], [
        ["AD-01", "Upgrade path", "Three releases with a bridge release", "Hazelcast removal tooling is not available on 8.8; stream provider switch should not be combined with a software update", "[R5, R30, R33]"],
        ["AD-02", "Bridge release", "Latest '24.1 patch (24.1.4 or later)", "Pega's documented adoption sequence names '24.1; 24.1.4 includes the Hazelcast removal changes without a hotfix", "[R2, R7]"],
        ["AD-03", "Kafka topics", "Drain and recreate; never copy Pega stream topics", "Pega does not support moving stream data between providers", "[R15, R30]"],
        ["AD-04", "Search indexes", "Rebuild through SRS from the database", "SRS indexes all searchable data after connection; embedded and plug-in data are not reusable", "[R17]"],
        ["AD-05", "Topic prefix at platform move", "New streamNamePattern prefix in Release 2", "Keeps the 8.8 topics untouched for rollback", "[R28]"],
        ["AD-06", "Index prefix at platform move", "New customerDeploymentId in Release 2", "Keeps the 8.8 indexes untouched for rollback; SRS isolates data by this ID", "[R16, R28]"],
        ["AD-07", "Confluent networking", "Private Link from the customer VNet", "Private connectivity for production data", "[R38]"],
        ["AD-08", "Kafka authentication", "SASL_SSL with PLAIN (service account API key)", "The documented Helm saslMechanism values are PLAIN, SCRAM-SHA-256 and SCRAM-SHA-512", "[R28]"],
        ["AD-09", "Secrets", "Key Vault with External Secrets Operator", "Supported by the Pega Helm chart; satisfies D-09", "[R28]"],
        ["AD-10", "Hazelcast removal method", "Downtime method (DSS) inside the Release 2 window", "Release 2 already has an outage; embedded Hazelcast needs no Clustering Service teardown", "[R8]"],
        ["AD-11", "Release 3 update type", "zero-downtime", "Supported from 8.4.2 and later; same platform and services", "[R28, R33]"],
        ["AD-12", "Search cluster sharing", "Pega environments only; no non-Pega workloads", "Pega best practice to avoid noisy neighbors", "[R16]"],
    ], caption="Architecture decisions", widths=[1.4, 2.9, 3.6, 6.8, 1.9], size=8.5)
    b.h2("Delivery option decision")
    b.p("{ref:fig_delivery} shows how the delivery option is chosen. The first question is settled for 8.8: it is not on a patch that "
        "can remove Hazelcast. The second question checks whether 8.8 can reach Confluent and SRS privately, which Release 1 "
        "needs. If it cannot, or if the business will not accept three windows, Releases 1 and 2 can be combined. That combined "
        "option changes the stream provider and the Pega version in one window, which goes against the Helm chart guidance [R30]; "
        "it should be used only after Pega Support confirms it for this estate.")
    b.figure(GEN + "fig_decision_delivery_option.png", "Decision: delivery option from 8.8 to 26.1.1", OWN, width_cm=14.5, label="delivery")
    b.h2("How open decisions are handled")
    b.p("Each open decision in Section 22 has an owner, a due point in the plan and a default. If a decision is not taken by "
        "its due point, the default applies and the risk is recorded in Section 21. A decision that changes a fixed decision "
        "(D-xx) needs approval from the customer enterprise architect and the security architect.")


def s6_aks(b):
    b.h1("Azure AKS platform design")
    b.p("The Pega Helm charts repository publishes a guide to deploying Pega Platform on AKS [R32]. This section applies "
        "that guide and the Pega client-managed cloud requirements [R22] to the customer's Azure landing zone.")
    b.h2("Pega requirements and how the design meets them")
    b.table(["Pega requirement", "Design", "Source"], [
        ["x86-64 CPUs only", "All node pools use x86-64 VM sizes (for example, Dsv5 or Esv5 families). No Arm-based (Ampere) sizes.", "[R22]"],
        ["At least two worker nodes with 32 GB RAM", "Pega node pool minimum of three nodes (one per zone), each 64 GiB or more.", "[R22]"],
        ["Database in the same region as workers", "Database and AKS in the same Azure region; zone-redundant database option.", "[R22]"],
        ["Tomcat from the Pega image", "Only Pega-provided platform/pega, platform/installer and SRS images, mirrored to Azure Container Registry.", "[R22, R28]"],
        ["Load balancer and TLS", "Application Gateway WAF v2 with the ingress controller; TLS to the pod using tier.service.tls.", "[R22, R28]"],
        ["External services", "Confluent Cloud (Kafka) and SRS with the search cluster. Cassandra only if CDH or Process AI is licensed.", "[R22]"],
    ], caption="Pega platform requirements and the AKS design", widths=[4.5, 10, 2.1], size=9)
    b.h2("Node pools")
    b.table(["Pool", "Purpose", "Sizing guidance", "Scheduling"], [
        ["system", "AKS system pods", "Three nodes across zones; AKS recommended system pool size", "CriticalAddonsOnly taint"],
        ["pega", "Web and batch tiers", "Start from the Pega tier defaults: CPU request 3, limit 4; memory 12 GiB; heap 8192m [R28]. Size so that each node holds at least two Pega pods with headroom for a rolling update.", "nodeSelector or affinity per tier; spread across zones"],
        ["srs", "SRS pods", "SRS minimum for production: three instances, 2 CPU and 2 GB each [R16]", "Can share a general user pool in non-production"],
    ], caption="AKS node pools", widths=[1.8, 3.2, 8, 3.6], size=9)
    b.callout("note", "The node counts above are starting points. Final sizes come from the load test in Section 16. Pega recommends leaving memory-based HPA disabled (hpa.enableMemoryTarget false) and scales on CPU by default, with hpa.targetAverageCPUValue 2.55 [R28].")
    b.h2("Network design")
    b.table(["Subnet or zone", "Contents", "Notes"], [
        ["AKS node subnet", "AKS nodes (and pods if Azure CNI Overlay is not used)", "Size for maximum nodes during upgrades (surge)."],
        ["Private endpoint subnet", "Private endpoints for Confluent (one per zone), search service, database, Key Vault, ACR", "Network policies for private endpoints enabled so NSGs apply."],
        ["Application Gateway subnet", "Application Gateway WAF v2", "Dedicated subnet, as required by Application Gateway."],
        ["Hub VNet (peered)", "Azure Firewall, private DNS resolver, shared services", "Default route from AKS to the firewall."],
    ], caption="Subnets", widths=[3.6, 7, 6], size=9)
    b.h3("Required network flows")
    b.table(["From", "To", "Port", "Protocol", "Purpose"], [
        ["Users", "Application Gateway", "443", "HTTPS", "Pega UI and APIs"],
        ["Application Gateway", "Web tier pods", "443 (tier TLS port)", "HTTPS", "Backend TLS"],
        ["Pega pods", "Confluent private endpoints", "9092 (and 443 for Confluent REST if used)", "SASL_SSL", "Stream service [R38]"],
        ["Pega pods", "SRS service", "SRS service port", "HTTP(S) with OAuth bearer", "Indexing and search"],
        ["SRS pods", "Search private endpoint", "443 or provider port (often 9200)", "HTTPS", "Index storage and queries"],
        ["Pega pods and installer", "Database private endpoint", "Engine port", "TLS", "Rules and data"],
        ["Pega and SRS pods", "OAuth token endpoint", "443", "HTTPS", "Client credentials token (Section 8.8)"],
        ["ESO pods", "Key Vault private endpoint", "443", "HTTPS", "Secret synchronization"],
        ["AKS nodes", "ACR private endpoint", "443", "HTTPS", "Image pulls"],
        ["Pega pods", "Pega Diagnostic Center", "443", "HTTPS", "Through the firewall, if PDC is used"],
    ], caption="Required network flows", widths=[3.1, 3.6, 3.4, 2.7, 3.8], size=8.5)
    b.h3("Private DNS")
    b.p("Every private endpoint needs a DNS record that resolves to its private IP from inside AKS. Azure Private DNS zones "
        "are linked to the spoke VNet or served by the hub DNS resolver [R46]. Confluent Private Link needs the bootstrap "
        "record and one record per zone, as Confluent describes for Azure [R38]. Missing zonal records are the most common "
        "cause of Kafka clients connecting to the bootstrap server and then failing on broker connections (Section 17).")
    b.table(["Service", "DNS zone", "Records"], [
        ["Confluent Cloud", "The Confluent network DNS domain shown in the Confluent Cloud console", "Wildcard and zonal records pointing at the private endpoint IPs, as listed in the Confluent console [R38]"],
        ["Key Vault", "privatelink.vaultcore.azure.net", "Vault name A record [R46]"],
        ["Container Registry", "privatelink.azurecr.io", "Registry and data endpoint records [R46]"],
        ["Database", "Engine-specific privatelink zone", "Server A record [R46]"],
        ["Search service", "Provider-specific zone", "As documented by the chosen provider (OD-04)"],
    ], caption="Private DNS zones", widths=[3.2, 6, 7.4], size=9)
    b.h2("Images and registry")
    b.steps([
        "Download platform/installer, platform/pega and platform-services/search-n-reporting-service (or the -os variant) for each release from Pega Digital Software Delivery [R33].",
        "Push them to Azure Container Registry under a repository per release, and scan them with the customer's image scanner.",
        "Reference images by tag and record the digest in Appendix A, so that every environment runs the same build.",
        "Grant AKS pull access through the kubelet managed identity (AcrPull role). Do not store registry passwords in values files.",
    ])
    b.h2("Availability settings")
    b.bullets([
        "Spread the web and batch tiers across three zones with topology spread constraints or pod anti-affinity.",
        "Enable a PodDisruptionBudget on each tier (pdb.enabled true; minAvailable 1 by default) so node upgrades cannot remove every pod of a tier [R28].",
        "Keep at least two web pods and two batch pods in production. Queue processors and job schedulers run on the batch tier and stop if no batch pod is available.",
        "Use the default Pega readiness and liveness probes from the Helm chart unless a load test shows a need to change them.",
    ])
