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
OLD = "#EDEDED"       # 8.8 estate

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


def decision(nid, text):
    return f'{nid} [shape=diamond, style="filled", fillcolor="{DEC}", label="{text}", margin="0.04,0.04", fontsize=9.5];'


def logical_flows():
    body = f'''
  rankdir=TB; nodesep=0.5; ranksep=0.55;
  u [label="User", shape=box, style="rounded"];
  ing [label="Application Gateway\\nand ingress", fillcolor="{AZ}"];
  web [label="Pega web tier", fillcolor="{PEGA}"];
  bat [label="Pega batch tier", fillcolor="{PEGA}"];
  db [label="Upgraded clone of the\\n8.8 database", shape=cylinder, style=filled, fillcolor="{AZ}"];
  k [label="Confluent Cloud\\ntopics pega-<env>-*", fillcolor="{EXT}"];
  srs [label="SRS (one per environment)", fillcolor="{BACK}"];
  os [label="Managed OpenSearch\\nindexes pega26-<env>*", fillcolor="{EXT}"];
  okta [label="Okta custom\\nauthorization server", fillcolor="{SEC}"];
  mon [label="Azure Monitor and SIEM", fillcolor="{AZ}"];
  u -> ing -> web [label="1 request", color="{NAVY}", fontcolor="{NAVY}", penwidth=1.6];
  web -> db [label="1 rules and case data", color="{NAVY}", fontcolor="{NAVY}", penwidth=1.6];
  web -> k [label="2 queue processor\\nmessages", color="#C55A11", fontcolor="#C55A11", penwidth=1.6];
  k -> bat [label="2 consume", color="#C55A11", fontcolor="#C55A11", penwidth=1.6];
  bat -> srs [label="3 index", color="#7030A0", fontcolor="#7030A0", penwidth=1.6];
  web -> srs [label="3 search query", color="#7030A0", fontcolor="#7030A0"];
  srs -> os [label="3 store and query", color="#7030A0", fontcolor="#7030A0", penwidth=1.6];
  web -> okta [label="4 token", style=dashed];
  srs -> okta [label="4 signing keys", style=dashed];
  web -> mon [label="5 telemetry", style=dotted];
  srs -> mon [style=dotted]; k -> mon [style=dotted]; os -> mon [style=dotted];
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
        ("Authentication", "SASL, OAuth token\\nor basic"),
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
        label="Work through the steps in order.\\nA failure at one step makes\\nevery later step fail.\\nKeep the evidence (Appendix D)."];
  {{rank=same; s4; note}}
  s0 -> s5 [style=invis];
'''
    render("fig_connectivity_chain", body)


def okta_token_flow():
    body = f'''
  rankdir=LR; nodesep=0.5;
  pega [label="Pega node\\n(web or batch)\\nclientId pega-srs-<env>", fillcolor="{PEGA}"];
  okta [label="Okta custom authorization server\\n/oauth2/<server-id>/v1/token\\nscope pega.search:full\\nclaim guid = pega26-<env>", fillcolor="{SEC}"];
  jwks [label="Okta key set\\njwks_uri from the\\ndiscovery document", fillcolor="{SEC}"];
  srs [label="SRS for <env>\\nAuthEnabled true\\nOAuthPublicKeyURL", fillcolor="{BACK}"];
  chk [label="SRS checks\\n1 signature (key set)\\n2 guid equals\\n   customerDeploymentId", shape=note, fillcolor="white"];
  os [label="Managed OpenSearch\\nindexes pega26-<env>*", fillcolor="{EXT}"];
  pega -> okta [label="1 client credentials grant\\nprivate_key_jwt (RS256),\\nkey from Key Vault"];
  okta -> pega [label="2 access token (JWT)", style=dashed];
  pega -> srs [label="3 request with\\nbearer token"];
  srs -> jwks [label="4 fetch signing keys\\n(through egress firewall)", style=dashed];
  srs -> chk [style=dotted, arrowhead=none];
  srs -> os [label="5 TLS + SRS user\\n(index-scoped role)"];
'''
    render("fig_okta_token_flow", body)


def secrets_flow():
    body = f'''
  rankdir=LR;
  kv [label="Azure Key Vault\\none vault per environment", fillcolor="{SEC}"];
  eso [label="External Secrets Operator\\n(workload identity)", fillcolor="{SEC}"];
  ks [label="Kubernetes secrets\\nin pega-<env> and srs-<env>", fillcolor="{AZ}"];
  pega [label="Pega web and batch pods\\njdbc.external_secret_name\\nstream.external_secret_name\\npegasearch.srsAuth.external_secret_name", fillcolor="{PEGA}"];
  inst [label="Installer job\\njdbc.external_secret_name", fillcolor="{PEGA}"];
  srs [label="SRS pods\\nsrsStorage.authSecret\\nsrsRuntime.ssl.certsSecret", fillcolor="{BACK}"];
  kv -> eso [label="read (Key Vault\\nSecrets User role)"];
  eso -> ks [label="sync on\\nrefreshInterval"];
  ks -> pega; ks -> inst; ks -> srs;
'''
    render("fig_secrets_flow", body)


def clone_upgrade_flow():
    body = f'''
  rankdir=TB; nodesep=0.3; ranksep=0.32;
  subgraph cluster_old {{ label="Pega 8.8 estate (unchanged)"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    p88 [label="Pega 8.8 production\\nembedded Kafka, embedded Elasticsearch", fillcolor="{OLD}"];
    db88 [label="8.8 production database", shape=cylinder, style=filled, fillcolor="{OLD}"];
    p88 -> db88 [arrowhead=none];
  }}
  clone [label="1 Clone the database\\n(production: final clone after 8.8 is stopped)", fillcolor="{AZ}"];
  {decision("np", "Non-production\\nenvironment?")}
  mask [label="2 Mask personal data\\n(customer masking policy)", fillcolor="{SEC}"];
  upg [label="3 Installer job: action upgrade\\nupgradeType per Pega Support (GQ-04)", fillcolor="{PEGA}"];
  clean [label="4 Clean-up and checks of cloned\\nKafka and search items (Section 10.3)", fillcolor="{DEC}"];
  dep [label="5 Deploy 26.1.1 tiers: own prefix,\\nservice account, customerDeploymentId\\nbatch tier at zero, intake held", fillcolor="{PEGA}"];
  chk [label="6 Stream and search landing pages,\\nqueue processors, cloned items", fillcolor="{DEC}"];
  idx [label="7 Scale batch tier; full index build\\nthrough SRS into OpenSearch", fillcolor="{BACK}"];
  rel [label="8 Release intake", fillcolor="{OK}"];
  db88 -> clone;
  clone -> np;
  np -> mask [label="Yes"];
  np -> upg [label="No (PROD)"];
  mask -> upg -> clean -> dep -> chk -> idx -> rel;
'''
    render("fig_clone_upgrade_flow", body)


def cutover_timeline():
    steps = [
        ("C-1", "Hold intake on 8.8\\nusers, listeners,\\nschedulers", OLD),
        ("C-2", "Drain queues\\nrecord zero counts\\nand broken items", OLD),
        ("C-3", "Stop 8.8\\nfinal clone", AZ),
        ("C-4", "Upgrade clone\\ninstaller job", PEGA),
        ("C-5", "Clean-up\\nand checks", DEC),
        ("C-6", "First start\\nintake held", PEGA),
        ("C-7", "Full index build\\ncount checks", BACK),
        ("C-8", "Application Kafka\\ndata sets cutover", EXT),
        ("C-9", "Smoke tests\\nGo/No-Go 2", DEC),
        ("C-10", "DNS switch\\nrelease intake", OK),
    ]
    nodes = " ".join(f'{s.replace("-", "")} [label="{s}\\n{t}", fillcolor="{c}", width=1.35];' for s, t, c in steps)
    ids = [s.replace("-", "") for s, _, _ in steps]
    body = f'''
  rankdir=TB; nodesep=0.3; ranksep=0.45; newrank=true;
  {nodes}
  {{rank=same; {"; ".join(ids[:5])}}}
  {{rank=same; {"; ".join(ids[5:])}}}
  {" -> ".join(ids[:5])};
  {" -> ".join(ids[5:])};
  C5 -> C6;
  rb [label="Rollback without loss of 26.1.1 work:\\nrestart 8.8 on its untouched database,\\nwith its embedded Kafka and Elasticsearch", fillcolor="{STOP}"];
  pnr [label="After C-10, rollback loses work done\\non 26.1.1 (business decision)", fillcolor="{STOP}"];
  C9 -> rb [style=dashed, label="any step\\nup to C-9"];
  C10 -> pnr [style=dashed];
'''
    render("fig_cutover_timeline", body)


def shared_topology():
    def envbox(code, name):
        return (f'{code} [label="{name} namespace pega-{code}\\nprefix pega-{code}-  |  sa-pega-{code}\\n'
                f'customerDeploymentId pega26-{code}\\nSRS srs-{code}  |  Okta client pega-srs-{code}", fillcolor="{PEGA}"];')
    body = f'''
  rankdir=LR; nodesep=0.25; ranksep=0.9; newrank=true;
  subgraph cluster_np1 {{ label="Shared group NP1 (functional)"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    {envbox("dev", "DEV")} {envbox("sit", "SIT")} {envbox("uat", "UAT")}
  }}
  subgraph cluster_np1s {{ label="NP1 services"; style="rounded"; color="{GREY}"; fontsize=10;
    k1 [label="Confluent cluster cc-np1\\nprefixed ACLs per service account\\nclient quota per service account", fillcolor="{EXT}"];
    o1 [label="OpenSearch os-np1\\none SRS user and role per environment\\nindex pattern pega26-<env>*", fillcolor="{EXT}"];
  }}
  subgraph cluster_np2 {{ label="Shared group NP2 (production-like)"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    {envbox("perf", "PERF")} {envbox("ppd", "PREPROD")}
  }}
  subgraph cluster_np2s {{ label="NP2 services (same type and settings as PROD)"; style="rounded"; color="{GREY}"; fontsize=10;
    k2 [label="Confluent cluster cc-np2", fillcolor="{EXT}"];
    o2 [label="OpenSearch os-np2", fillcolor="{EXT}"];
  }}
  dev -> k1; sit -> k1; uat -> k1;
  dev -> o1 [style=dashed]; sit -> o1 [style=dashed]; uat -> o1 [style=dashed];
  perf -> k2; ppd -> k2;
  perf -> o2 [style=dashed]; ppd -> o2 [style=dashed];
  note [shape=note, fillcolor="white", fontsize=9, label="Solid: Kafka (SASL_SSL, Private Link)\\nDashed: SRS to OpenSearch (TLS, private endpoint)\\nEach environment has its own Key Vault secrets"];
'''
    render("fig_shared_topology", body)


def prod_topology():
    body = f'''
  rankdir=LR; nodesep=0.35; ranksep=0.7;
  subgraph cluster_aks {{ label="Production AKS cluster"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    web [label="Web tier\\n(WebUser)", fillcolor="{PEGA}"];
    bat [label="Batch tier\\n(BackgroundProcessing,\\nSearch, Batch, RealTime ...)", fillcolor="{PEGA}"];
    srs [label="SRS srs-prd\\n3 replicas, network policy", fillcolor="{BACK}"];
    eso [label="External Secrets\\nOperator", fillcolor="{SEC}"];
  }}
  k [label="Confluent cluster cc-prd\\n(dedicated to PROD)\\nprefix pega-prd-, sa-pega-prd", fillcolor="{EXT}"];
  o [label="OpenSearch os-prd\\n(dedicated to PROD)\\n3 cluster-manager, 3+ data nodes", fillcolor="{EXT}"];
  okta [label="Okta custom authorization\\nserver for PROD only", fillcolor="{SEC}"];
  kv [label="Key Vault kv-pega-prd", fillcolor="{SEC}"];
  db [label="Upgraded final clone\\n(PROD database)", shape=cylinder, style=filled, fillcolor="{AZ}"];
  web -> k; bat -> k;
  web -> srs; bat -> srs;
  srs -> o;
  web -> okta [style=dashed]; srs -> okta [style=dashed, label="key set"];
  kv -> eso [style=dotted];
  web -> db; bat -> db;
'''
    render("fig_prod_topology", body)


def network_dns_flow():
    body = f'''
  rankdir=LR; nodesep=0.3; ranksep=0.55;
  pod [label="Pega or SRS pod", fillcolor="{PEGA}"];
  core [label="CoreDNS\\n(AKS)", fillcolor="{AZ}"];
  res [label="Hub DNS resolver\\nor Azure DNS", fillcolor="{AZ}"];
  z1 [label="Private DNS zone for the\\nConfluent network domain\\nwildcard and zonal records", fillcolor="{AZ}"];
  z2 [label="Private DNS zone for the\\nOpenSearch provider endpoint", fillcolor="{AZ}"];
  pe1 [label="Private endpoints (one per zone)\\nto Confluent Private Link service", fillcolor="{EXT}"];
  pe2 [label="Private endpoint to the\\nOpenSearch provider", fillcolor="{EXT}"];
  fw [label="Hub firewall\\negress allow-list", fillcolor="{STOP}"];
  okta [label="Okta (public SaaS)\\n<okta-domain>:443", fillcolor="{SEC}"];
  pod -> core -> res;
  res -> z1 [label="bootstrap and\\nbroker names"];
  res -> z2 [label="search host"];
  pod -> pe1 [label="9092 SASL_SSL", color="#C55A11", fontcolor="#C55A11"];
  pod -> pe2 [label="443 HTTPS", color="#7030A0", fontcolor="#7030A0"];
  pod -> fw [label="443 token and key set"];
  fw -> okta;
'''
    render("fig_network_dns", body)


def message_path():
    body = f'''
  rankdir=LR; nodesep=0.3; ranksep=0.55;
  prod [label="Producer on any tier\\n(queue-for-processing step,\\njob scheduler, Pega service)", fillcolor="{PEGA}"];
  qp [label="Queue processor rule\\n(stream name)", fillcolor="{PEGA}"];
  topic [label="Topic pega-<env>-<stream name>\\npartitions 0..n\\nreplication factor 3", fillcolor="{EXT}"];
  cg [label="Consumer group\\nunder prefix pega-<env>-", fillcolor="{EXT}"];
  bat [label="Batch tier pods\\none partition is read by\\none consumer at a time", fillcolor="{PEGA}"];
  db [label="Database\\n(delayed and broken\\nitems, case data)", shape=cylinder, style=filled, fillcolor="{AZ}"];
  prod -> qp [label="queue item"];
  qp -> topic [label="produce\\n(idempotent, transactional)"];
  topic -> cg [arrowhead=none];
  cg -> bat [label="consume"];
  bat -> db [label="process; failed items\\nbecome broken items"];
  prod -> db [style=dashed, label="delayed items wait in\\nthe database until due"];
'''
    render("fig_message_path", body)


def decision_env_grouping():
    body = f'''
  rankdir=TB;
  start [label="Place a non-production environment on shared services", fillcolor="{PEGA}"];
  {decision("q1", "Does it run load tests\\nor production rehearsals?")}
  {decision("q2", "Must it match PROD service\\ntype, settings and\\nnetworking?")}
  {decision("q3", "Can its schedule avoid\\noverlap with the other\\nproduction-like environment?")}
  np1 [label="Shared group NP1\\n(DEV, SIT, UAT)", fillcolor="{OK}"];
  np2 [label="Shared group NP2\\n(PERF, PREPROD)", fillcolor="{OK}"];
  own [label="Own service set\\n(extra cost, logged as a decision)", fillcolor="{DEC}"];
  start -> q1;
  q1 -> np1 [label="No"];
  q1 -> q2 [label="Yes"];
  q2 -> np1 [label="No"];
  q2 -> q3 [label="Yes"];
  q3 -> np2 [label="Yes"];
  q3 -> own [label="No"];
'''
    render("fig_decision_env_grouping", body)


def decision_srs():
    body = f'''
  rankdir=TB;
  start [label="One SRS per environment, or one shared SRS?", fillcolor="{PEGA}"];
  {decision("q1", "Is the environment PROD?")}
  {decision("q2", "Must SRS upgrades and\\nrestarts be planned per\\nenvironment?")}
  {decision("q3", "Must each environment use\\nits own OpenSearch user\\nand index-scoped role?")}
  per [label="RECOMMENDED: SRS per environment\\nin namespace srs-<env>\\nown OpenSearch user, own key set URL", fillcolor="{OK}"];
  shared [label="Shared SRS for the group\\nisolation by customerDeploymentId only;\\none OpenSearch user for all", fillcolor="{DEC}"];
  start -> q1;
  q1 -> per [label="Yes"];
  q1 -> q2 [label="No"];
  q2 -> per [label="Yes"];
  q2 -> q3 [label="No"];
  q3 -> per [label="Yes"];
  q3 -> shared [label="No"];
'''
    render("fig_decision_srs", body)


def decision_search_provider():
    body = f'''
  rankdir=TB;
  start [label="Select the managed OpenSearch provider", fillcolor="{PEGA}"];
  {decision("q1", "Provider documentation shows\\nan Azure region and OpenSearch\\n2.15 or 2.19 (SRS matrix)?")}
  {decision("q2", "Private connectivity from\\nthe customer VNet\\n(private endpoint)?")}
  {decision("q3", "Can the customer set\\nauto_create_index and\\ndestructive_requires_name?")}
  {decision("q4", "Fine-grained roles with\\nindex patterns, snapshots,\\nsupport terms accepted?")}
  ok [label="Candidate: score as in Section 7.3\\nimage search-n-reporting-service-os", fillcolor="{OK}"];
  self [label="Fallback: self-managed OpenSearch\\n(official images) on a dedicated\\nAKS node pool; customer operates it", fillcolor="{DEC}"];
  reject [label="Reject the provider", fillcolor="{STOP}"];
  start -> q1;
  q1 -> q2 [label="Yes"]; q1 -> reject [label="No"];
  q2 -> q3 [label="Yes"]; q2 -> reject [label="No"];
  q3 -> q4 [label="Yes"]; q3 -> reject [label="No"];
  q4 -> ok [label="Yes"]; q4 -> reject [label="No"];
  reject -> self [style=dashed, label="no provider passes"];
'''
    render("fig_decision_search_provider", body)


def decision_confluent():
    body = f'''
  rankdir=TB;
  start [label="Select the Confluent Cloud cluster type", fillcolor="{PEGA}"];
  {decision("q1", "Holds cloned or masked\\nproduction data?")}
  {decision("q2", "Need VNet peering, or more\\nthan 32 eCKU with\\nPrivate Link?")}
  {decision("q3", "Measured partitions and\\nthroughput within\\nEnterprise limits?")}
  basic [label="Basic or Standard\\n(sandbox only, no cloned data)", fillcolor="{DEC}"];
  ent [label="Enterprise\\nPrivate Link", fillcolor="{OK}"];
  ded [label="Dedicated\\nPrivate Link or VNet peering", fillcolor="{OK}"];
  frt [label="Freight: not suitable\\n(no idempotent producer,\\nno transactions)", fillcolor="{STOP}"];
  start -> q1;
  q1 -> basic [label="No"];
  q1 -> q2 [label="Yes"];
  q2 -> ded [label="Yes"];
  q2 -> q3 [label="No"];
  q3 -> ent [label="Yes"];
  q3 -> ded [label="No"];
  start -> frt [style=dashed, arrowhead=none];
'''
    render("fig_decision_confluent", body)


def decision_kafka_auth():
    body = f'''
  rankdir=TB;
  start [label="Select Pega to Kafka authentication", fillcolor="{PEGA}"];
  {decision("q1", "Documented Helm value\\nfor the mechanism\\n(stream.saslMechanism)?")}
  {decision("q2", "Security policy forbids\\nlong-lived API keys?")}
  {decision("q3", "OAUTHBEARER proven with\\nConfluent in a 26.1.1\\nrehearsal?")}
  plain [label="SASL_SSL + PLAIN\\nservice-account API key in Key Vault,\\nrotated by runbook (reference design)", fillcolor="{OK}"];
  oauth [label="SASL_SSL + OAUTHBEARER\\nper the Pega article", fillcolor="{OK}"];
  exc [label="Exception: PLAIN with short\\nrotation until OAUTHBEARER\\nis proven", fillcolor="{DEC}"];
  start -> q1;
  q1 -> q2 [label="PLAIN: yes"];
  q2 -> plain [label="No"];
  q2 -> q3 [label="Yes"];
  q3 -> oauth [label="Yes"];
  q3 -> exc [label="No"];
'''
    render("fig_decision_kafka_auth", body)


def decision_cloned_item():
    body = f'''
  rankdir=TB;
  start [label="Item found in the cloned database (Section 10.3)", fillcolor="{PEGA}"];
  {decision("q1", "Does it point to a Kafka,\\nsearch or other endpoint\\noutside this environment?")}
  {decision("q2", "Does Pega 26.1.1 replace\\nit with Helm or SRS\\nconfiguration?")}
  {decision("q3", "Does Pega document\\nit as removed in\\n'25 or '26?")}
  {decision("q4", "Is it business work\\n(queue item, case,\\nscheduled run)?")}
  rep [label="CHANGE: repoint or disable\\nbefore the batch tier starts", fillcolor="{STOP}"];
  chk [label="CHECK after first start:\\nlanding page shows the Helm value;\\nraise with Pega Support if not", fillcolor="{DEC}"];
  del [label="DELETE with the Pega-documented\\nmethod (for example PEGA0179 DSS)", fillcolor="{DEC}"];
  biz [label="DECIDE per kind with the business:\\nresolve on 8.8, reprocess on 26.1.1,\\nor discard (non-production)", fillcolor="{DEC}"];
  keep [label="KEEP", fillcolor="{OK}"];
  start -> q1;
  q1 -> rep [label="Yes"]; q1 -> q2 [label="No"];
  q2 -> chk [label="Yes"]; q2 -> q3 [label="No"];
  q3 -> del [label="Yes"]; q3 -> q4 [label="No"];
  q4 -> biz [label="Yes"]; q4 -> keep [label="No"];
'''
    render("fig_decision_cloned_item", body)


def decision_migration():
    body = f'''
  rankdir=TB;
  start [label="8.8 content that touches Kafka or search", fillcolor="{PEGA}"];
  {decision("q1", "Pega stream data in the\\n8.8 embedded Kafka?")}
  {decision("q2", "Search index in the 8.8\\nembedded Elasticsearch?")}
  {decision("q3", "Queue item held in\\nthe database?")}
  {decision("q4", "Application Kafka data set\\non the customer's own\\nKafka cluster?")}
  drain [label="NOT MIGRATED: hold intake, drain on 8.8,\\nrecord zero counts. 26.1.1 creates\\nempty topics under its own prefix", fillcolor="{OK}"];
  rebuild [label="NOT MIGRATED: full index build\\nthrough SRS from the upgraded\\ndatabase", fillcolor="{OK}"];
  clone [label="TRAVELS WITH THE CLONE:\\nhandle as in Section 10.3,\\ntest in rehearsal", fillcolor="{DEC}"];
  ds [label="DECIDE PER DATA SET\\n(Section 11.3)", fillcolor="{DEC}"];
  start -> q1;
  q1 -> drain [label="Yes"]; q1 -> q2 [label="No"];
  q2 -> rebuild [label="Yes"]; q2 -> q3 [label="No"];
  q3 -> clone [label="Yes"]; q3 -> q4 [label="No"];
  q4 -> ds [label="Yes"];
'''
    render("fig_decision_migration", body)


def decision_app_datasets():
    body = f'''
  rankdir=TB;
  start [label="Application Kafka data set (one at a time)", fillcolor="{PEGA}"];
  {decision("q1", "Environment is\\nPROD?")}
  {decision("q2", "Will the customer's\\nKafka cluster stay\\nthe same?")}
  {decision("q3", "Does the consumer need\\nmessages still only\\nin the old cluster?")}
  np [label="NON-PRODUCTION: repoint to a test\\ntopic or disable before the batch\\ntier starts; never read PROD topics", fillcolor="{STOP}"];
  keep [label="KEEP: same cluster and topic;\\nagree start offset with 8.8 last\\ncommitted offset (evidence)", fillcolor="{OK}"];
  newo [label="NEW CLUSTER: start from\\nnew records only after cutover;\\nrecord last 8.8 offsets", fillcolor="{OK}"];
  cl [label="NEW CLUSTER WITH HISTORY:\\nConfluent Cluster Linking mirror\\n(offsets kept), promote at cutover", fillcolor="{OK}"];
  start -> q1;
  q1 -> np [label="No"];
  q1 -> q2 [label="Yes"];
  q2 -> keep [label="Yes"];
  q2 -> q3 [label="No"];
  q3 -> newo [label="No"];
  q3 -> cl [label="Yes"];
'''
    render("fig_decision_app_datasets", body)


def decision_first_start():
    body = f'''
  rankdir=TB; ranksep=0.3;
  start [label="First start of an environment built from a clone", fillcolor="{PEGA}"];
  {decision("q1", "Installer job completed\\nand log reviewed?")}
  {decision("q2", "Clean-up items in\\nSection 10.3 signed off?")}
  {decision("q3", "Stream landing page:\\nExternalKafka, NORMAL,\\nown prefix?")}
  {decision("q4", "Search landing page:\\nSRS connected, own\\ncustomerDeploymentId?")}
  {decision("q5", "No connection attempts to\\nPROD or other environments\\nin firewall logs?")}
  {decision("q6", "Index build complete,\\ncounts match database?")}
  go [label="GO: release intake", fillcolor="{OK}"];
  stop [label="NO-GO: keep intake held,\\nfix, repeat the failed check", fillcolor="{STOP}"];
  start -> q1;
  q1 -> q2 [label="Yes"]; q2 -> q3 [label="Yes"]; q3 -> q4 [label="Yes"];
  q4 -> q5 [label="Yes"]; q5 -> q6 [label="Yes"]; q6 -> go [label="Yes"];
  q1 -> stop [label="No"]; q2 -> stop [label="No"]; q3 -> stop [label="No"];
  q4 -> stop [label="No"]; q5 -> stop [label="No"]; q6 -> stop [label="No"];
'''
    render("fig_decision_first_start", body)


def troubleshoot_kafka():
    body = f'''
  rankdir=TB; ranksep=0.3;
  start [label="Stream status not NORMAL, or queue processors stuck", fillcolor="{STOP}"];
  {decision("q0", "Stream landing page shows\\nthe Helm bootstrap and\\nprefix (not 8.8 values)?")}
  {decision("q1", "nslookup of bootstrap\\nreturns private IP?")}
  {decision("q2", "openssl s_client to\\nbootstrap:9092 completes\\nTLS?")}
  {decision("q3", "kcat -L lists brokers and\\nall broker names resolve\\nprivately?")}
  {decision("q4", "Pega log shows SASL\\nauthentication failure?")}
  {decision("q5", "Pega log shows topic or\\ngroup authorization\\nerror?")}
  {decision("q6", "Producer errors on\\nrecord size?")}
  f0 [label="Stale cloned setting: follow\\nSection 10.3 item CD-01; restart", fillcolor="{DEC}"];
  f1 [label="Fix private DNS zone record\\nor VNet link", fillcolor="{DEC}"];
  f2 [label="Check firewall, network policy,\\nprivate endpoint state", fillcolor="{DEC}"];
  f3 [label="Add zonal broker records;\\nconfirm endpoints Approved", fillcolor="{DEC}"];
  f4 [label="Correct STREAM_JAAS_CONFIG\\nin Key Vault; re-sync; restart", fillcolor="{DEC}"];
  f5 [label="Fix PREFIXED ACLs; add\\nTRANSACTIONAL_ID and\\nIDEMPOTENT_WRITE", fillcolor="{DEC}"];
  f6 [label="Raise topic max.message.bytes\\nto 5,000,000", fillcolor="{DEC}"];
  f7 [label="Collect evidence; open Pega and\\nConfluent support cases", fillcolor="{PEGA}"];
  start -> q0;
  q0 -> f0 [label="No"]; q0 -> q1 [label="Yes"];
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
  {decision("q1", "SRS pods Ready\\n(kubectl get pods\\n-n srs-<env>)?")}
  {decision("q2", "Pega reaches the SRS\\nservice URL from a\\npega pod?")}
  {decision("q3", "SRS logs show 401 or 403\\nfrom token checks?")}
  {decision("q4", "OpenSearch cluster\\nhealth green or yellow?")}
  {decision("q5", "Indexing backlog or\\nbroken items on the\\nindexer queue processor?")}
  f1 [label="Check SRS to OpenSearch:\\nDNS, TLS, authSecret, role", fillcolor="{DEC}"];
  f2 [label="Check pegasearch.externalURL\\nand network policy pega to srs", fillcolor="{DEC}"];
  f3 [label="Decode token: scope, guid,\\nissuer; check OAuthPublicKeyURL\\nand firewall rule to Okta", fillcolor="{DEC}"];
  f4 [label="Fix cluster: disk watermark,\\nshard allocation, node loss", fillcolor="{DEC}"];
  f5 [label="Kafka path problem: use the\\nKafka tree; then requeue", fillcolor="{DEC}"];
  f6 [label="Check index status on the Search\\nlanding page; reindex the class", fillcolor="{PEGA}"];
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
  rankdir=LR; nodesep=0.16; ranksep=0.7;
  subgraph cluster_src {{ label="Sources (every signal carries the environment code)"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    pega [label="Pega web and batch pods\\nPegaRULES and ALERT logs to stdout\\nGC log file tailed by the agent", fillcolor="{PEGA}"];
    pdcag [label="Pega health, alerts\\nand exceptions", fillcolor="{PEGA}"];
    srs [label="SRS pods\\nlogs to stdout", fillcolor="{BACK}"];
    aks [label="AKS nodes, pods, HPA\\nand control plane", fillcolor="{AZ}"];
    syn [label="Synthetic check CronJob\\nper namespace (K, S, O checks)", fillcolor="{AZ}"];
    ccm [label="Confluent Metrics API\\n/export, by principal", fillcolor="{EXT}"];
    cca [label="Confluent audit log cluster\\nconfluent-audit-log-events", fillcolor="{EXT}"];
    osm [label="OpenSearch provider metrics\\nslow logs, audit logs", fillcolor="{EXT}"];
    okl [label="Okta System Log\\ntoken and rate-limit events", fillcolor="{SEC}"];
    fwl [label="Azure Firewall and\\nflow logs", fillcolor="{AZ}"];
  }}
  subgraph cluster_col {{ label="Collection"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    ama [label="Azure Monitor agent\\ncontainer log collection", fillcolor="{AZ}"];
    prom [label="Managed Prometheus\\nscrape jobs", fillcolor="{AZ}"];
    conn [label="SIEM connectors\\nand consumers", fillcolor="{SEC}"];
  }}
  subgraph cluster_store {{ label="Stores"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    law [label="Log Analytics\\nnon-production and production\\nworkspaces", fillcolor="{AZ}"];
    amw [label="Azure Monitor workspace\\n(Prometheus metrics)", fillcolor="{AZ}"];
    siem [label="SIEM", fillcolor="{SEC}"];
    pdc [label="Pega Diagnostic Center\\n(one monitored system\\nper environment)", fillcolor="{PEGA}"];
  }}
  subgraph cluster_use {{ label="Use"; style="dashed,rounded"; color="{GREY}"; fontsize=10;
    graf [label="Grafana dashboards\\nper environment and\\nper shared group", fillcolor="{OK}"];
    alert [label="Alert rules\\nto on-call by tier", fillcolor="{OK}"];
    soc [label="Security operations", fillcolor="{SEC}"];
  }}
  pega -> ama; srs -> ama; aks -> ama; syn -> ama;
  aks -> prom; syn -> prom; ccm -> prom [label="HTTPS scrape"]; osm -> prom [label="if exposed"];
  cca -> conn; okl -> conn; fwl -> law;
  osm -> law [label="provider export", style=dashed];
  pdcag -> pdc [label="HTTPS, one way"];
  ama -> law; prom -> amw; conn -> siem; law -> siem [label="security events"];
  law -> graf; amw -> graf; law -> alert; amw -> alert; pdc -> alert [style=dashed, label="notifications"];
  siem -> soc;
'''
    render("fig_observability", body)


def zone_resilience():
    def zone(n):
        return f'''
  subgraph cluster_z{n} {{ label="Availability zone {n}"; style="rounded"; color="{GREY}"; fontsize=10;
    w{n} [label="Web pod", fillcolor="{PEGA}"];
    b{n} [label="Batch pod", fillcolor="{PEGA}"];
    s{n} [label="SRS pod", fillcolor="{BACK}"];
    pe{n} [label="Confluent private\\nendpoint (zonal)", fillcolor="{AZ}"];
    om{n} [label="OpenSearch\\ncluster-manager", fillcolor="{EXT}"];
    od{n} [label="OpenSearch\\ndata node", fillcolor="{EXT}"];
    br{n} [label="Kafka brokers\\n(Confluent managed)", fillcolor="{EXT}"];
  }}'''
    body = f'''
  rankdir=TB; nodesep=0.25; ranksep=0.4; newrank=true;
  agw [label="Application Gateway v2\\nzone-redundant", fillcolor="{AZ}"];
  fw [label="Azure Firewall\\nzone-redundant", fillcolor="{AZ}"];
  {zone(1)} {zone(2)} {zone(3)}
  db [label="Pega database\\nzone-redundant high availability", shape=cylinder, style=filled, fillcolor="{AZ}"];
  kv [label="Key Vault\\n(regional, zone-resilient)", fillcolor="{SEC}"];
  agw -> w1; agw -> w2; agw -> w3;
  w1 -> b1 [style=invis]; w2 -> b2 [style=invis]; w3 -> b3 [style=invis];
  b1 -> s1 [style=invis]; b2 -> s2 [style=invis]; b3 -> s3 [style=invis];
  s1 -> pe1 [style=invis]; s2 -> pe2 [style=invis]; s3 -> pe3 [style=invis];
  pe1 -> br1; pe2 -> br2; pe3 -> br3;
  br1 -> om1 [style=invis]; br2 -> om2 [style=invis]; br3 -> om3 [style=invis];
  om1 -> od1 [style=invis]; om2 -> od2 [style=invis]; om3 -> od3 [style=invis];
  od1 -> db [style=invis]; od2 -> db [style=invis]; od3 -> kv [style=invis];
  fw -> agw [style=invis];
  note [shape=note, fillcolor="white", fontsize=9, label="Rule: losing any one zone leaves enough Pega pods,\\nSRS pods, OpenSearch replicas and Kafka replicas\\nto carry peak load. Node pools are sized at 1.5 times\\npeak so two zones hold the full load."];
  {{ rank=same; agw; fw; note; }}
'''
    render("fig_zone_resilience", body)


def env_waves():
    body = f'''
  rankdir=TB; nodesep=0.5; ranksep=0.55;
  w0 [label="Wave 0  Foundations\\nlanding zone, hub firewall,\\nprivate DNS, ACR, pipelines,\\nOkta authorization servers,\\nmonitoring workspaces", fillcolor="{AZ}"];
  w1 [label="Wave 1  DEV\\nnew: cc-np1, os-np1,\\nPrivate Link and DNS for NP1\\nproves every step, the Okta\\nclaim, the role and the clone", fillcolor="{PEGA}"];
  w2 [label="Wave 2  SIT, then UAT\\nnew: per-environment objects only\\nreuse: NP1 services\\nisolation tests IT-01 to IT-10", fillcolor="{PEGA}"];
  w3 [label="Wave 3  PERF\\nnew: cc-np2, os-np2 at PROD type\\nfull-size clone, load tests,\\nindex build timing, sizing", fillcolor="{PEGA}"];
  w4 [label="Wave 4  PREPROD\\nnew: per-environment objects only\\nreuse: NP2 services\\ntwo timed rehearsals", fillcolor="{PEGA}"];
  w5 [label="Wave 5  PROD\\nnew: cc-prd, os-prd, PROD Okta\\nserver, kv-pega-prd\\nfinal clone and cutover", fillcolor="{OK}"];
  w0 -> w1 [label="connectivity\\nchecks pass"];
  w1 -> w2 [label="DEV first-start\\nGo/No-Go (M2)"];
  w2 -> w3 [label="isolation\\ntests pass"];
  w3 -> w4 [label="PROD sizes\\nagreed (M3)"];
  w4 -> w5 [label="Go/No-Go 1\\n(M4, M5)"];
  {{ rank=same; w0; w1; w2; }}
  {{ rank=same; w3; w4; w5; }}
'''
    render("fig_env_waves", body)


def perf_harness():
    body = f'''
  rankdir=TB; nodesep=0.35; ranksep=0.45;
  lg [label="Load generators\\n(own subnet, outside\\nthe Pega node pools)", fillcolor="{AZ}"];
  agw [label="Application Gateway", fillcolor="{AZ}"];
  web [label="Web tier", fillcolor="{PEGA}"];
  k [label="Confluent cc-np2\\nprefix pega-perf-", fillcolor="{EXT}"];
  bat [label="Batch tier\\nqueue processors", fillcolor="{PEGA}"];
  srs [label="SRS srs-perf", fillcolor="{BACK}"];
  os [label="OpenSearch os-np2", fillcolor="{EXT}"];
  db [label="Pega database\\n(full-size masked clone)", shape=cylinder, style=filled, fillcolor="{AZ}"];
  okta [label="Okta", fillcolor="{SEC}"];
  lg -> agw -> web;
  web -> k [label="enqueue"]; k -> bat [label="consume"];
  web -> db; bat -> db;
  bat -> srs [label="index"]; web -> srs [label="query"]; srs -> os;
  web -> okta [style=dashed]; bat -> okta [style=dashed];
  m1 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M1 response time\\nand errors per journey"];
  m2 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M2 pod CPU, heap,\\nGC, HPA events"];
  m3 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M3 bytes, requests,\\nconnections, lag, throttle"];
  m4 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M4 ready to process,\\nthroughput, broken items"];
  m5 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M5 query latency,\\nindexing rate, rejections"];
  m6 [shape=ellipse, fillcolor="{DEC}", fontsize=9, label="M6 database CPU,\\nwaits, connections"];
  m1 -> lg [style=dotted, arrowhead=none]; m2 -> web [style=dotted, arrowhead=none];
  m3 -> k [style=dotted, arrowhead=none]; m4 -> bat [style=dotted, arrowhead=none];
  m5 -> os [style=dotted, arrowhead=none]; m6 -> db [style=dotted, arrowhead=none];
'''
    render("fig_perf_harness", body)


def sizing_flow():
    body = f'''
  rankdir=LR; nodesep=0.3; ranksep=0.45;
  i1 [label="8.8 production facts\\npeak users, case volumes,\\nqueue item rates, search rate", fillcolor="{OLD}"];
  i2 [label="DEV measurements\\ntopics, partitions, connections\\nper pod, index size", fillcolor="{PEGA}"];
  calc [label="Sizing calculator\\nKafka units, OpenSearch nodes\\nand storage, AKS nodes,\\ntoken rate", fillcolor="{EXT}"];
  perf [label="PERF load tests\\nat production volume", fillcolor="{PEGA}"];
  {decision("ok", "Targets met\\nwith headroom?")}
  adj [label="Adjust inputs\\nor sizes", fillcolor="{STOP}"];
  sign [label="PROD sizes signed\\noff at M3", fillcolor="{OK}"];
  run [label="Production monitoring\\nquarterly capacity review", fillcolor="{AZ}"];
  i1 -> calc; i2 -> calc; calc -> perf -> ok;
  ok -> adj [label="no"]; adj -> calc;
  ok -> sign [label="yes"]; sign -> run; run -> calc [style=dashed, label="actual usage"];
'''
    render("fig_sizing_flow", body)


def isolation_layers():
    rows = [
        ("Network", "Firewall allow-list per environment; network policies deny by default", "Same"),
        ("Identity", "Service account sa-pega-&lt;env&gt;; own API key", "OpenSearch user srs-&lt;env&gt;; Okta client pega-srs-&lt;env&gt;"),
        ("Authorization", "TOPIC and GROUP ACLs on prefix pega-&lt;env&gt;-", "Role on pega26-&lt;env&gt;*; guid claim checked by SRS"),
        ("Naming", "streamNamePattern pega-&lt;env&gt;-{stream.name}", "customerDeploymentId pega26-&lt;env&gt;"),
        ("Capacity", "Client quota per service account", "Build schedule; data nodes sized for one build"),
        ("Secrets", "Key Vault kv-pega-&lt;env&gt;; workload identity per namespace", "Same"),
        ("Proof", "IT-01 to IT-04, IT-08 to IT-10", "IT-05 to IT-07"),
    ]
    cells = "".join(
        f'<TR><TD BGCOLOR="{NAVY}" ALIGN="LEFT"><FONT COLOR="white"><B>{a}</B></FONT></TD>'
        f'<TD BGCOLOR="{EXT}" ALIGN="LEFT">{k}</TD><TD BGCOLOR="{BACK}" ALIGN="LEFT">{s}</TD></TR>'
        for a, k, s in rows)
    body = f'''
  t [shape=plaintext, style="", label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="2" CELLPADDING="6" COLOR="{LINE}">
  <TR><TD BGCOLOR="white"><B>Layer</B></TD><TD BGCOLOR="white"><B>Kafka (Confluent Cloud)</B></TD><TD BGCOLOR="white"><B>Search (SRS and OpenSearch)</B></TD></TR>
  {cells}</TABLE>>];
'''
    render("fig_isolation_layers", body)


if __name__ == "__main__":
    for old in OUT.glob("*"):
        if old.name not in ("fig_target_architecture.png",):
            old.unlink()
    logical_flows()
    connectivity_chain()
    okta_token_flow()
    secrets_flow()
    clone_upgrade_flow()
    cutover_timeline()
    shared_topology()
    prod_topology()
    network_dns_flow()
    message_path()
    decision_env_grouping()
    decision_srs()
    decision_search_provider()
    decision_confluent()
    decision_kafka_auth()
    decision_cloned_item()
    decision_migration()
    decision_app_datasets()
    decision_first_start()
    troubleshoot_kafka()
    troubleshoot_search()
    observability()
    zone_resilience()
    env_waves()
    perf_harness()
    sizing_flow()
    isolation_layers()
