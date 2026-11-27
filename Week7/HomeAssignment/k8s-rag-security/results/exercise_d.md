# Exercise D - Same question, different results

Strategy: **markdown** | embedder: **BAAI/bge-small-en-v1.5** | top-5 | distance = pgvector cosine distance (`<=>`, lower is closer)

`Authorized` is verified by an independent oracle (users.json x manifest.json), not by the database.


## How does a Kubernetes Deployment manage application replicas?

Primary knowledge area: **Application Engineering**  
Unrestricted top-5 (admin reference, never shown to users): APP-01 (restricted), APP-01 (restricted), APP-02 (restricted), APP-10 (restricted), APP-02 (restricted)


**Priya** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | APP-01 | Deployments | [concepts/workloads/controllers/deployment/](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | 0.1563 | YES |
| 2 | APP-01 | Deployments > Writing a Deployment Spec > Replicas | [concepts/workloads/controllers/deployment/](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | 0.1751 | YES |
| 3 | APP-02 | ReplicaSet > What's next | [concepts/workloads/controllers/replicaset/](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/) | 0.1945 | YES |
| 4 | APP-10 | Horizontal Pod Autoscaling > Autoscaling during rolling update | [concepts/workloads/autoscaling/horizontal-pod-autoscale/](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) | 0.1988 | YES |
| 5 | APP-02 | ReplicaSet > Alternatives to ReplicaSet | [concepts/workloads/controllers/replicaset/](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/) | 0.2050 | YES |

**Arjun** - 5 authorized results; withheld by RLS: APP-01, APP-02, APP-10

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2164 | YES |
| 2 | SHARED-04 | Objects In Kubernetes > Understanding Kubernetes objects > Object spec and status | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2165 | YES |
| 3 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2167 | YES |
| 4 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2270 | YES |
| 5 | PLAT-01 | Persistent Volumes | [concepts/storage/persistent-volumes/](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) | 0.2367 | YES |

**Meena** - 5 authorized results; withheld by RLS: APP-01, APP-02, APP-10

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2164 | YES |
| 2 | SHARED-04 | Objects In Kubernetes > Understanding Kubernetes objects > Object spec and status | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2165 | YES |
| 3 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2167 | YES |
| 4 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2270 | YES |
| 5 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2385 | YES |

**Divya** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | APP-01 | Deployments | [concepts/workloads/controllers/deployment/](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | 0.1563 | YES |
| 2 | APP-01 | Deployments > Writing a Deployment Spec > Replicas | [concepts/workloads/controllers/deployment/](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | 0.1751 | YES |
| 3 | APP-02 | ReplicaSet > What's next | [concepts/workloads/controllers/replicaset/](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/) | 0.1945 | YES |
| 4 | APP-10 | Horizontal Pod Autoscaling > Autoscaling during rolling update | [concepts/workloads/autoscaling/horizontal-pod-autoscale/](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) | 0.1988 | YES |
| 5 | APP-02 | ReplicaSet > Alternatives to ReplicaSet | [concepts/workloads/controllers/replicaset/](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/) | 0.2050 | YES |

## What are PersistentVolumes and PersistentVolumeClaims?

Primary knowledge area: **Platform Engineering**  
Unrestricted top-5 (admin reference, never shown to users): PLAT-01 (restricted), PLAT-01 (restricted), PLAT-01 (restricted), PLAT-02 (restricted), APP-03 (restricted)


**Priya** - 5 authorized results; withheld by RLS: PLAT-01, PLAT-02

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | APP-03 | StatefulSets > Pod Identity > Stable Storage | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.2278 | YES |
| 2 | APP-03 | StatefulSets > Components > Volume Claim Templates | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.2485 | YES |
| 3 | APP-03 | StatefulSets > Revision history > Managing Revision History > Best Practices > Avoid | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.3046 | YES |
| 4 | APP-03 | StatefulSets > Revision history > Managing Revision History > Best Practices > Avoid | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.3299 | YES |
| 5 | APP-03 | StatefulSets > PersistentVolumeClaim retention > Replicas | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.3404 | YES |

**Arjun** - 5 authorized results; withheld by RLS: APP-03

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | PLAT-01 | Persistent Volumes | [concepts/storage/persistent-volumes/](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) | 0.1633 | YES |
| 2 | PLAT-01 | Persistent Volumes > PersistentVolumeClaims | [concepts/storage/persistent-volumes/](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) | 0.2116 | YES |
| 3 | PLAT-01 | Persistent Volumes | [concepts/storage/persistent-volumes/](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) | 0.2131 | YES |
| 4 | PLAT-02 | Volumes > Types of volumes > Volumes that use a PersistentVolumeClaim | [concepts/storage/volumes/](https://kubernetes.io/docs/concepts/storage/volumes/) | 0.2190 | YES |
| 5 | PLAT-05 | Volume Snapshots > Lifecycle of a volume snapshot and volume snapshot content > Persistent Volume Claim as Snapshot Source Protection | [concepts/storage/volume-snapshots/](https://kubernetes.io/docs/concepts/storage/volume-snapshots/) | 0.2302 | YES |

**Meena** - 5 authorized results; withheld by RLS: PLAT-01, PLAT-02, APP-03

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SEC-05 | Multi-tenancy > Data Plane Isolation > Storage isolation | [concepts/security/multi-tenancy/](https://kubernetes.io/docs/concepts/security/multi-tenancy/) | 0.2919 | YES |
| 2 | SEC-01 | Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Persistent volume creation | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2983 | YES |
| 3 | SHARED-03 | The Kubernetes API > Persistence | [concepts/overview/kubernetes-api/](https://kubernetes.io/docs/concepts/overview/kubernetes-api/) | 0.3693 | YES |
| 4 | SHARED-03 | The Kubernetes API > Persistence | [concepts/overview/kubernetes-api/](https://kubernetes.io/docs/concepts/overview/kubernetes-api/) | 0.3989 | YES |
| 5 | SEC-04 | Security Checklist > Admission controllers | [concepts/security/security-checklist/](https://kubernetes.io/docs/concepts/security/security-checklist/) | 0.4121 | YES |

**Divya** - 5 authorized results; withheld by RLS: PLAT-01, PLAT-02

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | APP-03 | StatefulSets > Pod Identity > Stable Storage | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.2278 | YES |
| 2 | APP-03 | StatefulSets > Components > Volume Claim Templates | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.2485 | YES |
| 3 | SEC-05 | Multi-tenancy > Data Plane Isolation > Storage isolation | [concepts/security/multi-tenancy/](https://kubernetes.io/docs/concepts/security/multi-tenancy/) | 0.2919 | YES |
| 4 | SEC-01 | Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks > Persistent volume creation | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2983 | YES |
| 5 | APP-03 | StatefulSets > Revision history > Managing Revision History > Best Practices > Avoid | [concepts/workloads/controllers/statefulset/](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) | 0.3046 | YES |

## What are recommended Kubernetes RBAC practices?

Primary knowledge area: **Security Engineering**  
Unrestricted top-5 (admin reference, never shown to users): SEC-01 (restricted), SEC-04 (restricted), SEC-03 (restricted), SEC-01 (restricted), SEC-01 (restricted)


**Priya** - 5 authorized results; withheld by RLS: SEC-01, SEC-04, SEC-03

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2872 | YES |
| 2 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2874 | YES |
| 3 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2885 | YES |
| 4 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2888 | YES |
| 5 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2930 | YES |

**Arjun** - 5 authorized results; withheld by RLS: SEC-01, SEC-04, SEC-03

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2872 | YES |
| 2 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2874 | YES |
| 3 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2885 | YES |
| 4 | SHARED-01 | Overview > Historical context for Kubernetes | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2888 | YES |
| 5 | SHARED-01 | Overview > Why you need Kubernetes and what it can do | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.2930 | YES |

**Meena** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SEC-01 | Role Based Access Control Good Practices | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.1420 | YES |
| 2 | SEC-04 | Security Checklist > What's next | [concepts/security/security-checklist/](https://kubernetes.io/docs/concepts/security/security-checklist/) | 0.1845 | YES |
| 3 | SEC-03 | Good practices for Kubernetes Secrets > Cluster administrators > Configure least-privilege access to Secrets | [concepts/security/secrets-good-practices/](https://kubernetes.io/docs/concepts/security/secrets-good-practices/) | 0.2144 | YES |
| 4 | SEC-01 | Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2435 | YES |
| 5 | SEC-01 | Role Based Access Control Good Practices > General good practice > Periodic review | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2494 | YES |

**Divya** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SEC-01 | Role Based Access Control Good Practices | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.1420 | YES |
| 2 | SEC-04 | Security Checklist > What's next | [concepts/security/security-checklist/](https://kubernetes.io/docs/concepts/security/security-checklist/) | 0.1845 | YES |
| 3 | SEC-03 | Good practices for Kubernetes Secrets > Cluster administrators > Configure least-privilege access to Secrets | [concepts/security/secrets-good-practices/](https://kubernetes.io/docs/concepts/security/secrets-good-practices/) | 0.2144 | YES |
| 4 | SEC-01 | Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2435 | YES |
| 5 | SEC-01 | Role Based Access Control Good Practices > General good practice > Periodic review | [concepts/security/rbac-good-practices/](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | 0.2494 | YES |

## What are the main Kubernetes components?

Primary knowledge area: **Shared knowledge**  
Unrestricted top-5 (admin reference, never shown to users): SHARED-02 (shared), SHARED-01 (shared), SHARED-02 (shared), SHARED-02 (shared), SHARED-04 (shared)


**Priya** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-02 | Kubernetes Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1383 | YES |
| 2 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.1764 | YES |
| 3 | SHARED-02 | Kubernetes Components > Core Components > Control Plane Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1885 | YES |
| 4 | SHARED-02 | Kubernetes Components > Flexibility in Architecture | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.2098 | YES |
| 5 | SHARED-04 | Objects In Kubernetes > What's next | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2119 | YES |

**Arjun** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-02 | Kubernetes Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1383 | YES |
| 2 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.1764 | YES |
| 3 | SHARED-02 | Kubernetes Components > Core Components > Control Plane Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1885 | YES |
| 4 | SHARED-02 | Kubernetes Components > Flexibility in Architecture | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.2098 | YES |
| 5 | SHARED-04 | Objects In Kubernetes > What's next | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2119 | YES |

**Meena** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-02 | Kubernetes Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1383 | YES |
| 2 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.1764 | YES |
| 3 | SHARED-02 | Kubernetes Components > Core Components > Control Plane Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1885 | YES |
| 4 | SHARED-02 | Kubernetes Components > Flexibility in Architecture | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.2098 | YES |
| 5 | SHARED-04 | Objects In Kubernetes > What's next | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2119 | YES |

**Divya** - 5 authorized results

| # | Document | Section | Source | Distance | Authorized |
|---|---|---|---|---|---|
| 1 | SHARED-02 | Kubernetes Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1383 | YES |
| 2 | SHARED-01 | Overview > What's next | [concepts/overview/](https://kubernetes.io/docs/concepts/overview/) | 0.1764 | YES |
| 3 | SHARED-02 | Kubernetes Components > Core Components > Control Plane Components | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.1885 | YES |
| 4 | SHARED-02 | Kubernetes Components > Flexibility in Architecture | [concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/) | 0.2098 | YES |
| 5 | SHARED-04 | Objects In Kubernetes > What's next | [concepts/overview/working-with-objects/](https://kubernetes.io/docs/concepts/overview/working-with-objects/) | 0.2119 | YES |

**Authorization violations across all 16 searches: 0**
