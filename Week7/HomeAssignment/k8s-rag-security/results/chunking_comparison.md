# Exercise A - Chunking comparison

Embedder: **BAAI/bge-small-en-v1.5** | corpus: 30 Kubernetes docs | identical input for every strategy

## Parameters

| Strategy | Configuration |
|---|---|
| fixed | 1000 chars, 150 overlap |
| recursive | 1000 chars, 150 overlap, separators ## > ### > #### > blank line > line > sentence > word |
| markdown | split at every heading; sections > 1200 chars split recursively (100 overlap); sections < 200 chars merged forward; breadcrumb prepended for embedding |
| semantic | sentence/list/code units, window +/-1, break at > p85 cosine distance, min 300 / max 1200 chars |

## Size and overlap

| Metric | fixed | recursive | markdown | semantic |
|---|---|---|---|---|
| Total chunks | 662 | 713 | 755 | 684 |
| Chunks per document | 22.1 | 23.8 | 25.2 | 22.8 |
| Avg size (chars) | 977 | 806 | 737 | 806 |
| Median size (chars) | 1000 | 856 | 757 | 863 |
| Min size (chars) | 161 | 94 | 57 | 23 |
| Max size (chars) | 1000 | 1000 | 1199 | 1200 |
| Std-dev size (chars) | 115 | 180 | 317 | 320 |
| Avg tokens (embedded text) | 239 | 198 | 192 | 197 |
| Max tokens | 480 | 443 | 515 | 534 |
| % chunks > 512 tokens (truncated) | 0.0 | 0.0 | 0.1 | 0.1 |
| % tiny chunks (< 100 chars) | 0.0 | 0.1 | 0.7 | 1.2 |
| Overlap configured (chars) | 150 | 150 | 100 | 0 |
| Overlap measured avg (chars) | 149 | 34 | 7 | 0 |

## Heading preservation and boundary quality (lower is better unless marked +)

| Metric | fixed | recursive | markdown | semantic |
|---|---|---|---|---|
| + % chunks starting at a heading | 0.5% | 37.2% | 62.9% | 10.4% |
| + % chunks whose embedded text carries its heading | 0.5% | 37.2% | 100.0% | 10.4% |
| % chunks spanning 2+ sections | 63.3% | 40.5% | 8.2% | 49.6% |
| % chunks ending in an orphan heading | 3.3% | 8.4% | 0.0% | 0.0% |
| % chunks starting mid-sentence | 82.0% | 7.2% | 3.7% | 3.2% |
| % chunks ending mid-sentence | 76.6% | 8.0% | 7.3% | 4.7% |
| % chunks cutting a code block | 13.6% | 2.1% | 1.9% | 1.5% |

## Retrieval quality (21 labelled questions, top-5, all chunks)

| Metric | fixed | recursive | markdown | semantic |
|---|---|---|---|---|
| hit@1 | **0.905** | 0.81 | **0.905** | **0.905** |
| hit@5 | **1.0** | **1.0** | 0.952 | 0.952 |
| MRR@5 | **0.929** | 0.883 | **0.929** | **0.929** |
| precision@5 | 0.705 | 0.695 | **0.724** | **0.724** |

### Rank of first relevant document per question (- = not in top 5)

| Question | Expected | fixed | recursive | markdown | semantic |
|---|---|---|---|---|---|
| How does a Kubernetes Deployment manage application replicas? | APP-01, APP-02 | 1 | 1 | 1 | 1 |
| How do I roll back a Deployment to a previous revision? | APP-01 | 1 | 1 | 1 | 1 |
| What guarantees does a StatefulSet provide about stable network identity and ordered deployment? | APP-03 | 1 | 1 | 1 | 1 |
| How do I run a Job on a repeating schedule using cron syntax? | APP-06 | 1 | 1 | 1 | 1 |
| What happens to a Pod if one of its init containers fails? | APP-09 | 1 | 1 | 1 | 1 |
| How does the Horizontal Pod Autoscaler calculate the desired number of replicas? | APP-10 | 1 | 3 | 1 | 1 |
| How do I make sure a copy of a Pod runs on every node? | APP-04 | 4 | 2 | 2 | 1 |
| What are PersistentVolumes and PersistentVolumeClaims? | PLAT-01 | 1 | 1 | 1 | 1 |
| What does the reclaimPolicy of a StorageClass control? | PLAT-03, PLAT-01 | 1 | 1 | 1 | 1 |
| How do I take a point-in-time snapshot of a volume? | PLAT-05 | 1 | 2 | 1 | 1 |
| How can I clone an existing PersistentVolumeClaim? | PLAT-09 | 4 | 5 | - | - |
| What is an emptyDir volume and when is it deleted? | PLAT-02, PLAT-06 | 1 | 1 | 1 | 2 |
| How are volumes provisioned automatically on demand? | PLAT-04, PLAT-03 | 1 | 1 | 1 | 1 |
| What are recommended Kubernetes RBAC practices? | SEC-01 | 1 | 1 | 1 | 1 |
| What is the difference between the privileged, baseline and restricted pod security profiles? | SEC-02 | 1 | 1 | 1 | 1 |
| How should Secrets be protected, for example with encryption at rest and least-privilege access? | SEC-03, SEC-04 | 1 | 1 | 1 | 1 |
| How can multiple teams safely share one cluster? | SEC-05 | 1 | 1 | 1 | 1 |
| What are the main Kubernetes components? | SHARED-02, SHARED-01 | 1 | 1 | 1 | 1 |
| What are namespaces used for? | SHARED-05 | 1 | 1 | 1 | 1 |
| How do clients discover the Kubernetes API and its OpenAPI schema? | SHARED-03 | 1 | 1 | 1 | 1 |
| What is the difference between an object's spec and status? | SHARED-04 | 1 | 1 | 1 | 1 |

## Boundary examples (taken automatically from the data)

**fixed - poor** (APP-01, after chunk 1):  
> ...* A Deployment named `nginx-deployment` is created, indicated by the `.metadata.name` field. This name will become the basis for the Repli  
> **‖ next chunk:** example: * A Deployment named `nginx-deployment` is created, indicated by the `.metadata.name` field. This name will become the basis for...

**recursive - good** (APP-01, after chunk 0):  
> ...manage ReplicaSets owned by a Deployment. Consider opening an issue in the main Kubernetes repository if your use case is not covered below.  
> **‖ next chunk:** ## Use Case The following are typical use cases for Deployments: * Create a Deployment to rollout a ReplicaSet. The ReplicaSet creates Pod...

**recursive - poor** (APP-01, after chunk 9):  
> ...is added to the ReplicaSet selector, Pod template labels, and in any existing Pods that the ReplicaSet might have. ## Updating a Deployment  
> **‖ next chunk:** ## Updating a Deployment **Note:** A Deployment's rollout is triggered if and only if the Deployment's Pod template (that is, `.spec.templa...

**markdown - good** (APP-01, after chunk 0):  
> ...manage ReplicaSets owned by a Deployment. Consider opening an issue in the main Kubernetes repository if your use case is not covered below.  
> **‖ next chunk:** ## Use Case The following are typical use cases for Deployments: * Create a Deployment to rollout a ReplicaSet. The ReplicaSet creates Pod...

**markdown - poor** (APP-01, after chunk 12):  
> ...es.io/revision=2 Selector: app=nginx Replicas: 3 desired | 3 updated | 3 total | 3 available | 0 unavailable  
> **‖ next chunk:** Replicas: 3 desired | 3 updated | 3 total | 3 available | 0 unavailable StrategyType: RollingUpdate MinReadySeco...

**semantic - good** (APP-01, after chunk 1):  
> ...lout. * Use the status of the Deployment as an indicator that a rollout has stuck. * Clean up older ReplicaSets that you don't need anymore.  
> **‖ next chunk:** ## Creating a Deployment The following is an example of a Deployment. It creates a ReplicaSet to bring up three `nginx` Pods: `[code sampl...

**semantic - poor** (APP-01, after chunk 15):  
> ...icaSet: nginx-deployment-1564180365 (3/3 replicas created) Events: Type Reason Age From Messa  
> **‖ next chunk:** ge ---- ------ ---- ---- ------- Normal ScalingReplicaSet 2m deployment-controller Scale...


Metric definitions: *mid-sentence* = chunk does not start with a capital/Markdown marker, or does not end with sentence punctuation, a list item, table row or code fence; *cutting a code block* = odd number of ``` fences; *orphan heading* = chunk's last line is a heading whose body went to the next chunk.
