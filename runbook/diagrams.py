"""Generate the customer-specific diagrams for the runbook with Graphviz.

Each diagram is written as DOT source and rendered to PNG at 220 DPI into
img/generated/. Run: python3 diagrams.py
"""
import pathlib
import subprocess

OUT = pathlib.Path(__file__).parent / "img" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

FONT = "Liberation Sans"
NAVY = "#1F3864"
GREY = "#595959"
LINE = "#44546A"
PEGA = "#DCE6F2"      # Pega workloads
BACK = "#E4DFEC"      # Pega backing services
EXT = "#E2EFDA"       # external managed services
AZ = "#F2F2F2"        # Azure platform services
SEC = "#FCE4D6"       # identity and secrets
DEC = "#FFF2CC"       # decision diamonds
OK = "#E2EFDA"
STOP = "#F8CBAD"

BASE = f'''
  graph [fontname="{FONT}", fontsize=11, bgcolor="white", pad="0.3", nodesep="0.35", ranksep="0.45", fontcolor="{NAVY}"];
  node  [fontname="{FONT}", fontsize=10, shape=box, style="rounded,filled", fillcolor="white", color="{LINE}", penwidth=1.1, margin="0.14,0.07"];
  edge  [fontname="{FONT}", fontsize=9, color="{LINE}", fontcolor="{GREY}", arrowsize=0.7, penwidth=1.0];
'''


def render(name, body, engine="dot"):
    src = f"digraph G {{\n{BASE}\n{body}\n}}\n"
    (OUT / f"{name}.dot").write_text(src)
    subprocess.run([engine, "-Tpng", "-Gdpi=220", "-o", str(OUT / f"{name}.png"), str(OUT / f"{name}.dot")], check=True)
    print("rendered", name)


def cluster(cid, label, inner, style="dashed", color=GREY, fill="white"):
    return f'''
  subgraph cluster_{cid} {{
    label="{label}"; labeljust="l"; style="{style},rounded"; color="{color}"; fillcolor="{fill}"; fontsize=10; margin=12;
    {inner}
  }}'''


def decision(nid, text):
    return f'{nid} [shape=diamond, style="filled", fillcolor="{DEC}", label="{text}", margin="0.04,0.04", fontsize=9.5];'


def outcome(nid, text, fill=OK):
    return f'{nid} [shape=box, style="rounded,filled", fillcolor="{fill}", label="{text}"];'


def logical_flows():
    body = f'''
  rankdir=TB; nodesep=0.5; ranksep=0.55;
  u [label="User", shape=box, style="rounded"];
  ing [label="Ingress", fillcolor="{AZ}"];
  web [label="Pega web tier", fillcolor="{PEGA}"];
  bat [label="Pega batch tier", fillcolor="{PEGA}"];
  db [label="Database", shape=cylinder, style=filled, fillcolor="{AZ}"];
  k [label="Confluent Cloud\\ntopics (pega- prefix)", fillcolor="{EXT}"];
  srs [label="SRS", fillcolor="{BACK}"];
  os [label="Search cluster", fillcolor="{EXT}"];
  ops [label="Platform team", shape=box, style="rounded"];
  ctl [label="AKS API, Confluent console,\\nsearch console (private)", fillcolor="{AZ}"];
  mon [label="Azure Monitor and SIEM", fillcolor="{AZ}"];
  u -> ing -> web [label="1 request", color="{NAVY}", fontcolor="{NAVY}", penwidth=1.6];
  web -> db [label="1 rules and case data", color="{NAVY}", fontcolor="{NAVY}", penwidth=1.6];
  web -> k [label="2 queue processor\\nmessages", color="#C55A11", fontcolor="#C55A11", penwidth=1.6];
  k -> bat [label="2 consume", color="#C55A11", fontcolor="#C55A11", penwidth=1.6];
  bat -> srs [label="3 index (incremental\\nindexer queue processor)", color="#7030A0", fontcolor="#7030A0", penwidth=1.6];
  web -> srs [label="3 search query", color="#7030A0", fontcolor="#7030A0"];
  srs -> os [label="3 store and query", color="#7030A0", fontcolor="#7030A0", penwidth=1.6];
  ops -> ctl [label="4 administration", style=dashed];
  web -> mon [label="5 telemetry", style=dotted];
  srs -> mon [style=dotted];
  k -> mon [style=dotted];
  os -> mon [style=dotted];
'''
    render("fig_logical_flows", body)


def connectivity_chain():
    steps = [
        ("DNS resolution", "name resolves to a\\nprivate IP"),
        ("Route", "UDR / firewall path\\nto private endpoint"),
        ("Network policy", "egress allowed from\\npod namespace"),
        ("TCP connect", "port 9092 or 443\\nreachable"),
        ("TLS handshake", "TLS 1.2+, SNI\\nmatches host"),
        ("Certificate", "chain trusted by\\nclient truststore"),
        ("Authentication", "SASL / OAuth / basic\\nor client certificate"),
        ("Authorization", "ACL or role allows\\nthe operation"),
        ("Operation", "produce, consume,\\nindex, search"),
    ]
    nodes = []
    for i, (t, d) in enumerate(steps):
        nodes.append(f's{i} [label="{i+1}. {t}\\n{d}", fillcolor="{PEGA if i < 4 else SEC if i < 8 else OK}", width=1.9];')
    body = f'''
  rankdir=LR; nodesep=0.3; ranksep=0.3; newrank=true;
  {' '.join(nodes)}
  s0 -> s1 -> s2 -> s3 -> s4;
  s5 -> s6 -> s7 -> s8;
  s4 -> s5 [constraint=false];
  {{rank=same; s0; s5}}
  {{rank=same; s1; s6}}
  {{rank=same; s2; s7}}
  {{rank=same; s3; s8}}
  note [shape=note, style=filled, fillcolor="white", color="{GREY}", fontsize=9,
        label="Work through the steps in order.\\nA failure at one step makes\\nevery later step fail.\\nRecord evidence (Appendix C)."];
  {{rank=same; s4; note}}
  s0 -> s5 [style=invis];
'''
    render("fig_connectivity_chain", body)


def srs_auth_flow():
    body = f'''
  rankdir=LR;
  pega [label="Pega node\\n(web or batch)", fillcolor="{PEGA}"];
  idp [label="OAuth identity provider\\ntoken endpoint", fillcolor="{SEC}"];
  srs [label="SRS\\nAuthEnabled: true", fillcolor="{BACK}"];
  jwks [label="Public key URL\\n(OAuthPublicKeyURL)", fillcolor="{SEC}"];
  os [label="Elasticsearch / OpenSearch\\nindexes prefixed with\\ncustomerDeploymentId", fillcolor="{EXT}"];
  pega -> idp [label="1 client credentials\\n(private_key_jwt or client_secret_basic)\\nscope pega.search:full"];
  idp -> pega [label="2 JWT with scp and guid claims", style=dashed];
  pega -> srs [label="3 request + bearer token"];
  srs -> jwks [label="4 fetch signing keys", style=dashed];
  srs -> os [label="5 TLS + basic auth, mTLS\\nor PKI client certificate"];
'''
    render("fig_srs_auth_flow", body)


def secrets_flow():
    body = f'''
  rankdir=LR;
  kv [label="Azure Key Vault\\nsecrets and certificates", fillcolor="{SEC}"];
  eso [label="External Secrets Operator\\n(workload identity)", fillcolor="{SEC}"];
  ks [label="Kubernetes secrets\\n(etcd encrypted with KMS)", fillcolor="{AZ}"];
  pega [label="Pega pods\\njdbc.external_secret_name\\nstream.external_secret_name\\nglobal.certificatesSecrets", fillcolor="{PEGA}"];
  srs [label="SRS pods\\nsrsStorage.authSecret\\nsrsStorage.certsSecret", fillcolor="{BACK}"];
  kv -> eso [label="read (RBAC: Key Vault Secrets User)"];
  eso -> ks [label="sync on refreshInterval"];
  ks -> pega; ks -> srs;
'''
    render("fig_secrets_flow", body)


def decision_search_backend():
    body = f'''
  rankdir=TB;
  start [label="Select search backend for SRS", shape=box, style="rounded,filled", fillcolor="{PEGA}"];
  {decision("q1", "Does Customer policy\\nallow Elasticsearch\\n(Elastic licence)?")}
  {decision("q2", "Is a managed OpenSearch\\nservice available in the\\nAzure region with private\\nconnectivity?")}
  {decision("q3", "Does the provider allow\\nauto_create_index=false and\\ndestructive_requires_name=false?")}
  {decision("q4", "Does the provider support an\\nSRS auth method: basic, TLS,\\nmTLS or PKI?")}
  es [label="Elasticsearch 8.x from the\\ncertified list\\nimage: search-n-reporting-service", fillcolor="{OK}"];
  os [label="Managed OpenSearch 2.19 or 2.15\\nimage: search-n-reporting-service-os", fillcolor="{OK}"];
  self [label="Self-managed OpenSearch\\n(official images only) on a\\ndedicated node pool; Customer\\noperates it", fillcolor="{DEC}"];
  reject [label="Reject provider\\nand re-evaluate", fillcolor="{STOP}"];
  start -> q1;
  q1 -> es [label="Yes"];
  q1 -> q2 [label="No (current\\nbaseline D-08)"];
  q2 -> q3 [label="Yes"];
  q2 -> self [label="No"];
  q3 -> q4 [label="Yes"];
  q3 -> reject [label="No"];
  q4 -> os [label="Yes"];
  q4 -> reject [label="No"];
  es -> q3 [style=dashed, label="same checks apply"];
'''
    render("fig_decision_search_backend", body)


def decision_confluent():
    body = f'''
  rankdir=TB;
  start [label="Select Confluent Cloud cluster type", fillcolor="{PEGA}"];
  {decision("q1", "Production or any\\nenvironment holding\\nreal data?")}
  {decision("q2", "Private networking\\nrequired by security\\npolicy?")}
  {decision("q3", "Need VNet peering, mTLS,\\nor more than 32 eCKU?")}
  {decision("q4", "Partition need within\\nlimit? (count after\\nrehearsal)")}
  basic [label="Basic or Standard\\n(non-production only)", fillcolor="{DEC}"];
  std [label="Standard\\n(public networking only)", fillcolor="{STOP}"];
  ent [label="Enterprise\\nPrivate Link (PrivateLink Attachment)", fillcolor="{OK}"];
  ded [label="Dedicated\\nPrivate Link or VNet peering", fillcolor="{OK}"];
  frt [label="Freight: not suitable\\n(no idempotent producer,\\nno transactions)", fillcolor="{STOP}"];
  start -> q1;
  q1 -> basic [label="No"];
  q1 -> q2 [label="Yes"];
  q2 -> std [label="No, but reference\\ndesign requires it"];
  q2 -> q3 [label="Yes"];
  q3 -> ded [label="Yes"];
  q3 -> q4 [label="No"];
  q4 -> ent [label="Yes"];
  q4 -> ded [label="No"];
  start -> frt [style=dashed, arrowhead=none];
'''
    render("fig_decision_confluent", body)


def decision_kafka_auth():
    body = f'''
  rankdir=TB;
  start [label="Select Pega to Kafka authentication", fillcolor="{PEGA}"];
  {decision("q1", "Is a documented\\nHelm path available for\\nthe mechanism in 26.1.1?")}
  {decision("q2", "Security policy forbids\\nlong-lived API keys?")}
  {decision("q3", "OAUTHBEARER proven in\\nPega 26.1.1 rehearsal\\nwith Confluent?")}
  plain [label="SASL_SSL + PLAIN\\nConfluent service-account API key\\nin Key Vault, rotated by runbook\\n(reference design)", fillcolor="{OK}"];
  oauth [label="SASL_SSL + OAUTHBEARER\\nper Pega article for OAuthBearer", fillcolor="{OK}"];
  exc [label="Raise exception: use PLAIN with\\nshort rotation interval until\\nOAUTHBEARER is proven", fillcolor="{DEC}"];
  start -> q1;
  q1 -> q2 [label="PLAIN: yes\\n(stream.saslMechanism)"];
  q2 -> plain [label="No"];
  q2 -> q3 [label="Yes"];
  q3 -> oauth [label="Yes"];
  q3 -> exc [label="No"];
'''
    render("fig_decision_kafka_auth", body)


def decision_source_path():
    body = f'''
  rankdir=TB;
  start [label="Assess the Pega 8.8 source estate", fillcolor="{PEGA}"];
  {decision("q1", "Source runs on\\nVMs or on\\nKubernetes?")}
  {decision("q2", "Stream: embedded\\nstream nodes or\\nexternal Kafka?")}
  {decision("q3", "Search: embedded,\\nlegacy plug-in\\nor SRS?")}
  vm [label="Side-by-side move to the new\\nAKS platform (VMs are not\\nsupported from \'25)", fillcolor="{OK}"];
  k8s [label="Side-by-side is still preferred\\nbecause the target is a new\\nAKS cluster and Confluent", fillcolor="{OK}"];
  s1 [label="Drain embedded stream with the\\nStream Migration activity (8.7+),\\nswitch to Confluent (Release 1)", fillcolor="{DEC}"];
  s2 [label="Drain external Kafka queues;\\nswitch provider to Confluent\\n(Release 1)", fillcolor="{DEC}"];
  r1 [label="Full index build through SRS\\n(Section 12)", fillcolor="{DEC}"];
  start -> q1;
  q1 -> vm [label="VMs"];
  q1 -> k8s [label="Kubernetes"];
  vm -> q2; k8s -> q2;
  q2 -> s1 [label="Embedded"];
  q2 -> s2 [label="External"];
  s1 -> q3; s2 -> q3;
  q3 -> r1 [label="Any of the three"];
'''
    render("fig_decision_source_path", body)


def decision_delivery_option():
    body = f"""
  rankdir=TB;
  start [label="Choose how to reach Pega 26.1.1 from 8.8", fillcolor="{PEGA}"];
  {decision("q1", "Is the source on 23.1.4,\\n24.1.3, 24.2.2 or a\\nlater patch?")}
  {decision("q2", "Can the 8.8 nodes reach\\nConfluent and SRS over\\nprivate networking?")}
  {decision("q3", "Can the business accept\\nthree change windows?")}
  direct [label="Remove Hazelcast on the source,\\nthen update to 26.1.1\\n(not the case for 8.8)", fillcolor="{AZ}"];
  three [label="RECOMMENDED: three releases\\nR1 externalize Kafka and search on 8.8\\nR2 move to AKS on the bridge release,\\nremove Hazelcast\\nR3 zero-downtime update to 26.1.1", fillcolor="{OK}"];
  two [label="Combined R1 + R2: switch Kafka\\nand search during the platform move;\\nthen R3. Deviation from Pega guidance:\\nconfirm with Pega Support first", fillcolor="{DEC}"];
  start -> q1;
  q1 -> direct [label="Yes"];
  q1 -> q2 [label="No (8.8)"];
  q2 -> q3 [label="Yes"];
  q2 -> two [label="No"];
  q3 -> three [label="Yes"];
  q3 -> two [label="No"];
"""
    render("fig_decision_delivery_option", body)


def decision_stream_data():
    body = f'''
  rankdir=TB;
  start [label="Topic or stream in scope", fillcolor="{PEGA}"];
  {decision("q1", "Pega platform topic\\n(stream.streamNamePattern\\nprefix)?")}
  {decision("q2", "Application Kafka data set\\non a separate Kafka\\nservice?")}
  {decision("q3", "Does the consumer need\\nhistory that is still\\nonly in Kafka?")}
  {decision("q4", "Is the source a Kafka\\ncluster that Cluster Linking\\ncan read?")}
  drain [label="DRAIN, do not copy.\\nRun Stream Migration activity until\\nqueueSize = 0 and COMPLETED.\\nTarget creates its topics empty\\n(new prefix at the platform move).", fillcolor="{OK}"];
  keep [label="Out of scope: the external\\nservice stays; repoint only if the\\napplication team requests it", fillcolor="{DEC}"];
  newo [label="Start data flow from\\n'only new records' after cutover;\\nrecord last offsets as evidence", fillcolor="{OK}"];
  cl [label="Cluster Linking mirror topics\\n(offsets preserved) then\\npromote at cutover", fillcolor="{OK}"];
  replay [label="Replay from the system of\\nrecord (database or source app)", fillcolor="{DEC}"];
  start -> q1;
  q1 -> drain [label="Yes"];
  q1 -> q2 [label="No"];
  q2 -> keep [label="Yes, unchanged"];
  q2 -> q3 [label="Moving to Confluent"];
  q3 -> newo [label="No"];
  q3 -> q4 [label="Yes"];
  q4 -> cl [label="Yes"];
  q4 -> replay [label="No"];
'''
    render("fig_decision_stream_data", body)


def decision_search_index():
    body = f"""
  rankdir=TB;
  start [label="Search indexes for each release", fillcolor="{PEGA}"];
  {decision("q1", "Does the source already\\nuse SRS on the target\\nsearch cluster?")}
  {decision("q2", "Does the rehearsal show a\\nfull index build fits the\\noutage window?")}
  r1 [label="Release 1: connect 8.8 to SRS and run\\nthe full index build (Pega documented\\npath; embedded and plug-in data\\nare not migrated)", fillcolor="{OK}"];
  newid [label="RECOMMENDED for Release 2:\\nnew customerDeploymentId, full build;\\nsource indexes stay intact for rollback", fillcolor="{OK}"];
  reuse [label="Keep customerDeploymentId; check index\\nstatus and re-index flagged classes;\\nrollback needs a re-index on 8.8", fillcolor="{DEC}"];
  snap [label="Snapshot copy of SRS indexes:\\nnot used. SRS owns index names and\\nmappings; ES 8 snapshots do not\\nrestore into OpenSearch", fillcolor="{STOP}"];
  start -> q1;
  q1 -> r1 [label="No (embedded or\\nlegacy plug-in)"];
  q1 -> q2 [label="Yes"];
  q2 -> newid [label="Yes"];
  q2 -> reuse [label="No"];
  start -> snap [style=dashed, arrowhead=none];
"""
    render("fig_decision_search_index", body)


def upgrade_path():
    body = f"""
  rankdir=TB; nodesep=0.3; ranksep=0.32;
  src [label="Pega 8.8 source (production)", fillcolor="{PEGA}"];
  p1 [label="Prepare on 8.8\\nUpdate Tools, Jakarta JAR review,\\nprimaryKeyUtility dry run,\\ncustom queue processor review", fillcolor="{DEC}"];
  p2 [label="Build target platform\\nAKS, Confluent, search cluster,\\nSRS, Key Vault, DNS, TLS", fillcolor="{AZ}"];
  subgraph cluster_r1 {{ label="Release 1: externalize on 8.8 (no Pega software change)"; style="dashed,rounded"; color="{GREY}";
    r1 [label="Drain stream, switch 8.8 to Confluent;\\nconnect 8.8 to SRS, full index build", fillcolor="{OK}"];
  }}
  subgraph cluster_r2 {{ label="Release 2: platform move to AKS on the bridge release"; style="dashed,rounded"; color="{GREY}";
    r2 [label="Drain, copy database, update to bridge\\n(24.1.4 or later patch), start on AKS\\nwith new topic prefix and index prefix", fillcolor="{OK}"];
    hz [label="Remove Hazelcast (DSS method)\\nin the same window", fillcolor="{OK}"];
  }}
  subgraph cluster_r3 {{ label="Release 3: release update on the same platform"; style="dashed,rounded"; color="{GREY}";
    r3 [label="Zero-downtime update to 26.1.1\\nsame AKS, Confluent and SRS", fillcolor="{OK}"];
  }}
  done [label="Hypercare, handover,\\ndecommission 8.8 estate", fillcolor="{OK}"];
  src -> p1 -> r1; p2 -> r1;
  r1 -> r2 [label="rehearsed on staging"];
  r2 -> hz;
  hz -> r3 [label="rehearsed on staging"];
  r3 -> done;
  {{rank=same; p1; p2}}
"""
    render("fig_upgrade_path", body)


def release1_flow():
    body = f"""
  rankdir=TB; nodesep=0.3; ranksep=0.3;
  a [label="Pre-checks: Confluent topics ACLs ready, SRS healthy,\\n8.8 nodes reach both privately (Section 17 chain)", fillcolor="{DEC}"];
  b [label="Confirm queue processors and data flows\\nto drain are RUNNING", fillcolor="{PEGA}"];
  c [label="Stop producers (web traffic, listeners,\\nproducer data flows)", fillcolor="{PEGA}"];
  d [label="POST .../pzstream/migration; poll GET until\\nqueueSize=0, timeToDrainMS=0, COMPLETED", fillcolor="{PEGA}"];
  e [label="Stop all 8.8 nodes", fillcolor="{PEGA}"];
  f [label="Configure 8.8 for Confluent (stream settings)\\nand SRS (search settings)", fillcolor="{BACK}"];
  g [label="Start all nodes; Stream landing page shows\\nProvider ExternalKafka, Status NORMAL", fillcolor="{BACK}"];
  h [label="Full index build through SRS (downtime);\\ncheck index status per class", fillcolor="{BACK}"];
  {decision("q", "Smoke and search\\ntests pass?")}
  ok [label="Re-open traffic; hypercare", fillcolor="{OK}"];
  rb [label="Rollback (Section 15)", fillcolor="{STOP}"];
  a -> b -> c -> d -> e -> f -> g -> h -> q;
  q -> ok [label="Yes"]; q -> rb [label="No"];
"""
    render("fig_release1_flow", body)


def stage2_flow():
    body = f'''
  rankdir=TB; nodesep=0.3; ranksep=0.32;
  a [label="Confirm Hazelcast removed\\n(hazelcast/disabled returns true)", fillcolor="{PEGA}"];
  b [label="Update SRS to a version listed for\\n26.1.1; confirm search cluster version", fillcolor="{BACK}"];
  c [label="Kafka readiness: client 4.0.0 compatibility,\\nSystemPulse topic 6 partitions,\\nremove DSS delayeditems/dataflowbased/threadspernode", fillcolor="{EXT}"];
  d [label="Code readiness: Jakarta EE JARs re-imported,\\nprimary keys present (primaryKeyUtility)", fillcolor="{DEC}"];
  e [label="Installer job, upgradeType zero-downtime\\nrules migrated and upgraded in new rules schema", fillcolor="{BACK}"];
  f [label="Rolling restart onto 26.1.1 images;\\ndata schema upgrade", fillcolor="{BACK}"];
  g [label="Verify Stream provider ExternalKafka / NORMAL,\\nsearch index status, queue processors", fillcolor="{OK}"];
  {decision("q", "Acceptance\\ntests pass?")}
  ok [label="Close change; hypercare", fillcolor="{OK}"];
  rb [label="Rollback (Section 15)", fillcolor="{STOP}"];
  a -> b -> c -> d -> e -> f -> g -> q;
  q -> ok [label="Yes"]; q -> rb [label="No"];
'''
    render("fig_stage2_flow", body)


def cutover_flow():
    body = f"""
  rankdir=TB; nodesep=0.3; ranksep=0.3;
  t0 [label="T-7d: Go/No-Go 1\\nrehearsal evidence accepted", fillcolor="{DEC}"];
  t1 [label="Change freeze on 8.8; announce outage window", fillcolor="{PEGA}"];
  t2 [label="Stop producers (web traffic and listeners)", fillcolor="{PEGA}"];
  t3 [label="Run Stream Migration activity; poll until\\nqueueSize=0, timeToDrainMS=0, COMPLETED", fillcolor="{PEGA}"];
  t4 [label="Stop all 8.8 nodes; final database backup", fillcolor="{PEGA}"];
  t5 [label="Restore database to target; installer job\\nupdates it to the bridge release", fillcolor="{BACK}"];
  t6 [label="Deploy bridge tiers on AKS (new topic prefix);\\nStream provider ExternalKafka / NORMAL", fillcolor="{BACK}"];
  t7 [label="Remove Hazelcast: set DSS, full stop and start,\\nverify hazelcast/disabled = true", fillcolor="{BACK}"];
  t8 [label="Full index build (new customerDeploymentId);\\nconfirm index status", fillcolor="{BACK}"];
  {decision("g2", "Go/No-Go 2\\nsmoke tests pass?")}
  t9 [label="Switch public DNS to Application Gateway", fillcolor="{OK}"];
  {decision("g3", "Go/No-Go 3\\nfirst 30 minutes\\nclean?")}
  t10 [label="Soak period; release freeze; hypercare", fillcolor="{OK}"];
  rb [label="Rollback (Section 15)", fillcolor="{STOP}"];
  t0 -> t1 -> t2 -> t3 -> t4 -> t5 -> t6 -> t7 -> t8 -> g2;
  g2 -> t9 [label="Yes"];
  g2 -> rb [label="No"];
  t9 -> g3;
  g3 -> t10 [label="Yes"];
  g3 -> rb [label="No"];
"""
    render("fig_cutover_flow", body)


def rollback_tree():
    body = f'''
  rankdir=TB;
  start [label="Rollback trigger raised", fillcolor="{STOP}"];
  {decision("q1", "Has public DNS been\\nswitched to the target?")}
  {decision("q2", "Have users created or\\nchanged cases on the\\ntarget?")}
  a [label="Abort: leave DNS on 8.8,\\nrestart 8.8 nodes on the original\\ndatabase, re-open intake", fillcolor="{OK}"];
  b [label="Revert DNS to 8.8; restart 8.8\\non original database; no data\\nreconciliation needed", fillcolor="{OK}"];
  c [label="Business decision required:\\nfix forward on 26.1.1, or revert and\\nre-key changes made since cutover\\n(see reconciliation report)", fillcolor="{DEC}"];
  start -> q1;
  q1 -> a [label="No"];
  q1 -> q2 [label="Yes"];
  q2 -> b [label="No"];
  q2 -> c [label="Yes"];
'''
    render("fig_rollback_tree", body)


def troubleshoot_kafka():
    body = f'''
  rankdir=TB; ranksep=0.3;
  start [label="Stream status not NORMAL, or queue processors stuck", fillcolor="{STOP}"];
  {decision("q1", "nslookup of bootstrap\\nreturns private IP?")}
  {decision("q2", "openssl s_client to\\nbootstrap:9092 completes\\nTLS?")}
  {decision("q3", "kcat -L lists brokers and\\nall broker names resolve\\nprivately?")}
  {decision("q4", "Pega log shows SASL\\nauthentication failure?")}
  {decision("q5", "Pega log shows topic or\\ngroup authorization\\nerror?")}
  {decision("q6", "Producer errors on\\nrecord size?")}
  f1 [label="Fix private DNS zone record\\nor VNet link", fillcolor="{DEC}"];
  f2 [label="Check NSG / firewall / network\\npolicy, private endpoint state", fillcolor="{DEC}"];
  f3 [label="Add zonal broker records;\\nconfirm all private endpoints\\nare Approved", fillcolor="{DEC}"];
  f4 [label="Correct STREAM_JAAS_CONFIG\\nin Key Vault; re-sync secret;\\nrestart pods", fillcolor="{DEC}"];
  f5 [label="Add PREFIXED ACLs for topic and\\ngroup; TRANSACTIONAL_ID and\\nIDEMPOTENT_WRITE", fillcolor="{DEC}"];
  f6 [label="Raise topic max.message.bytes\\nor align stream.producer.* JVM args", fillcolor="{DEC}"];
  f7 [label="Collect evidence; open Pega and\\nConfluent support cases", fillcolor="{PEGA}"];
  start -> q1;
  q1 -> f1 [label="No"]; q1 -> q2 [label="Yes"];
  q2 -> f2 [label="No"]; q2 -> q3 [label="Yes"];
  q3 -> f3 [label="No"]; q3 -> q4 [label="Yes"];
  q4 -> f4 [label="Yes"]; q4 -> q5 [label="No"];
  q5 -> f5 [label="Yes"]; q5 -> q6 [label="No"];
  q6 -> f6 [label="Yes"]; q6 -> f7 [label="No"];
'''
    render("fig_troubleshoot_kafka", body)


def troubleshoot_search():
    body = f'''
  rankdir=TB; ranksep=0.3;
  start [label="Search fails or results are stale", fillcolor="{STOP}"];
  {decision("q1", "SRS pods Ready\\n(kubectl get pods -n srs)?")}
  {decision("q2", "Pega can reach SRS\\nservice URL from a\\npega pod?")}
  {decision("q3", "SRS logs show 401/403\\nfrom token validation?")}
  {decision("q4", "Search cluster health\\ngreen or yellow?")}
  {decision("q5", "Incremental indexer queue\\nprocessor backlog or\\nbroken items?")}
  f1 [label="Check readiness probe, search\\nconnectivity from SRS pod,\\nauthSecret / certsSecret", fillcolor="{DEC}"];
  f2 [label="Check pegasearch.externalURL,\\nnetwork policy pega to srs", fillcolor="{DEC}"];
  f3 [label="Check token claims scp and guid,\\nOAuthPublicKeyURL, clock skew", fillcolor="{DEC}"];
  f4 [label="Fix cluster: disk watermark,\\nshard allocation, node loss", fillcolor="{DEC}"];
  f5 [label="Kafka path problem: use Kafka\\ntree; then requeue broken items", fillcolor="{DEC}"];
  f6 [label="Check index status on the Search\\nlanding page; reindex class", fillcolor="{PEGA}"];
  start -> q1;
  q1 -> f1 [label="No"]; q1 -> q2 [label="Yes"];
  q2 -> f2 [label="No"]; q2 -> q3 [label="Yes"];
  q3 -> f3 [label="Yes"]; q3 -> q4 [label="No"];
  q4 -> f4 [label="Red"]; q4 -> q5 [label="Yes"];
  q5 -> f5 [label="Yes"]; q5 -> f6 [label="No"];
'''
    render("fig_troubleshoot_search", body)


def observability():
    body = f'''
  rankdir=LR;
  pega [label="Pega web and batch\\nlogs, JVM, PDC alerts", fillcolor="{PEGA}"];
  srs [label="SRS pods\\nlogs, latency, errors", fillcolor="{BACK}"];
  aks [label="AKS nodes and pods\\nContainer Insights", fillcolor="{AZ}"];
  ccl [label="Confluent Cloud\\nMetrics API, audit log topic", fillcolor="{EXT}"];
  srch [label="Search service\\nhealth, latency, disk, JVM", fillcolor="{EXT}"];
  net [label="Synthetic checks\\nDNS, TCP, TLS expiry", fillcolor="{AZ}"];
  law [label="Log Analytics workspace\\nand Azure Monitor metrics", fillcolor="{AZ}"];
  pdc [label="Pega Diagnostic Center", fillcolor="{PEGA}"];
  siem [label="SIEM", fillcolor="{SEC}"];
  dash [label="Platform dashboard\\n(7 distinct health signals)", fillcolor="{OK}"];
  alert [label="Alert rules and on-call\\nrouting (Section 18)", fillcolor="{OK}"];
  pega -> law; srs -> law; aks -> law; net -> law;
  ccl -> law [label="exporter / connector"];
  srch -> law [label="provider integration"];
  pega -> pdc [style=dashed];
  law -> siem [label="security events"];
  law -> dash; law -> alert;
'''
    render("fig_observability", body)


def migration_workstreams():
    body = f'''
  rankdir=LR; nodesep=0.2; ranksep=0.35;
  subgraph cluster_prep {{ label="Phase 1 Prepare"; style="dashed,rounded"; color="{GREY}";
    a [label="A0 Upgrade readiness\\n(8.8 assessment)", fillcolor="{DEC}"];
    b [label="B Kafka platform\\n(Confluent, network)", fillcolor="{EXT}"];
    e [label="E SRS and search\\nplatform", fillcolor="{EXT}"];
  }}
  subgraph cluster_build {{ label="Phase 2 Build and rehearse"; style="dashed,rounded"; color="{GREY}";
    a1 [label="A Pega config and\\ndatabase update\\n(bridge, then 26.1.1)", fillcolor="{PEGA}"];
    c [label="C Topics and ACLs", fillcolor="{EXT}"];
    f [label="F Index rebuild", fillcolor="{BACK}"];
  }}
  subgraph cluster_cut {{ label="Phase 3 Cut over"; style="dashed,rounded"; color="{GREY}";
    d [label="D Stream drain and\\nconsumer state", fillcolor="{PEGA}"];
    g [label="G DNS and TLS", fillcolor="{AZ}"];
    h [label="H Application cutover", fillcolor="{OK}"];
  }}
  i [label="I Operational handover", fillcolor="{OK}"];
  a -> a1; b -> c; e -> f; a1 -> d; c -> d; f -> h; d -> h; g -> h; h -> i;
'''
    render("fig_migration_workstreams", body)


if __name__ == "__main__":
    logical_flows()
    connectivity_chain()
    srs_auth_flow()
    secrets_flow()
    decision_search_backend()
    decision_confluent()
    decision_kafka_auth()
    decision_source_path()
    decision_delivery_option()
    decision_stream_data()
    decision_search_index()
    upgrade_path()
    release1_flow()
    stage2_flow()
    cutover_flow()
    rollback_tree()
    troubleshoot_kafka()
    troubleshoot_search()
    observability()
    migration_workstreams()
