---
title: "NovaCloud Customer Support Policy and SLAs"
visibility: "PUBLIC"
category: "support_policy"
---

# NovaCloud Customer Support Policy and SLAs

This policy outlines NovaCloud's standard customer support framework, service level agreements (SLAs), support tier definitions, and official communication channels.

---

## 1. Scope of Support Services

NovaCloud provides 24/7 technical support for infrastructure services under the cloud shared responsibility model:

### Covered Services:
* Platform availability and hypervisor operational integrity
* Physical datacenter facilities, hardware switches, and power redundancy
* NovaCloud Management Console, Cloud APIs, and billing services
* Core cloud networking components (Internet Gateways, VPC routing, DNS resolvers, Security Groups)

### Out-of-Scope Services:
* Debugging third-party customer application code or proprietary algorithms
* Database query optimization and software-level data migration scripts
* Guest operating system application administration outside base platform compatibility

---

## 2. Support Tiers and Response Time SLAs

NovaCloud offers three customer support tiers:

| Support Plan | Severity 1 (Critical Outage) | Severity 2 (Degraded Production) | Severity 3 (General Guidance) |
| :--- | :--- | :--- | :--- |
| **Basic Support** | Next Business Day | 24 Hours | 48 Hours |
| **Business Tier** | Under 1 Hour | Under 4 Hours | 12 Hours |
| **Enterprise Tier** | Under 15 Minutes | Under 1 Hour | 4 Hours |

### Incident Severity Definitions:
* **Severity 1 (Critical)**: Production service is completely down with widespread customer business impact.
* **Severity 2 (High)**: Core features are degraded, but critical systems remain partially operational.
* **Severity 3 (Standard)**: Non-urgent inquiries, feature requests, or development environment setup questions.

---

## 3. Official Customer Support Channels

Customers can contact NovaCloud Technical Support through authorized public channels:
* **NovaCloud Web Portal**: Submit and track technical tickets via `https://support.novacloud.internal/portal` (Mock URL).
* **Automated Support Bot (NovaBot)**: Interactive assistant available directly within the console for instant troubleshooting.
* **Status Page**: Check real-time cloud region health and planned maintenance notices at `https://status.novacloud.internal` (Mock URL).

---

## 4. Scheduled Maintenance and Downtime Notifications

* **Advance Notification**: NovaCloud provides a minimum of **5 business days** advance notice for all scheduled platform maintenance windows.
* **Emergency Maintenance**: In cases of critical security patches (e.g., zero-day kernel vulnerabilities), NovaCloud reserves the right to execute emergency maintenance with notification dispatched as early as feasible.
