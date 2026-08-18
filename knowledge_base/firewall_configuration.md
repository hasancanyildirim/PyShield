---
title: "NovaCloud Firewall and Security Groups Configuration Guide"
visibility: "PUBLIC"
category: "networking"
---

# NovaCloud Firewall and Security Groups Configuration Guide

NovaCloud Security Groups act as distributed, stateful virtual firewalls that control inbound (ingress) and outbound (egress) network traffic at the virtual network interface card (vNIC) layer.

---

## 1. Core Principles of NovaCloud Security Groups

* **Stateful Filtering**: Security groups are stateful. If you permit an inbound request on a specific port, return outbound traffic is automatically permitted, regardless of outbound rule definitions.
* **Default Deny Inbound**: All inbound traffic is blocked by default until explicit permit rules are added.
* **Default Allow Outbound**: By default, all outbound traffic from an instance to external destinations is permitted unless explicitly restricted.
* **Rule Composition**: Each rule consists of a Protocol (TCP, UDP, ICMP), Port Range, Source/Destination CIDR block or Security Group ID, and Description.

---

## 2. Configuring Inbound Rules for Common Workloads

To expose public services, add specific inbound rules in the NovaCloud Console under **Networking > Security Groups > Inbound Rules**:

### Web Services (HTTP / HTTPS)
* **HTTP Rule**: Protocol: `TCP`, Port: `80`, Source: `0.0.0.0/0` (Any IPv4 address) or `::/0` (IPv6).
* **HTTPS Rule**: Protocol: `TCP`, Port: `443`, Source: `0.0.0.0/0` (Any IPv4 address).

### Secure Remote Management
* **SSH (Linux)**: Protocol: `TCP`, Port: `22`, Source: Limit to your corporate static IP (e.g., `203.0.113.50/32`) instead of `0.0.0.0/0` to mitigate brute-force attacks.
* **RDP (Windows)**: Protocol: `TCP`, Port: `3389`, Source: Limit to authorized administrative subnets or VPN gateway endpoints.

### Database Clusters
* **PostgreSQL**: Protocol: `TCP`, Port: `5432`, Source: Reference the Application Tier Security Group ID (e.g., `sg-web-tier-01`) rather than raw IP addresses.
* **MySQL / MariaDB**: Protocol: `TCP`, Port: `3306`, Source: Application Tier Security Group ID.

---

## 3. Stateful Firewall vs. Stateless Network ACLs

NovaCloud provides two complementary layers of network filtering:
1. **Security Groups (Instance Level)**: Stateful, evaluated at the instance vNIC. Rules specify permit actions only.
2. **Network Access Control Lists / NACLs (Subnet Level)**: Stateless, evaluated at the subnet boundary. NACLs evaluate numbered rules in sequential order (permit and deny actions) for both inbound and outbound traffic.

When debugging blocked traffic, always check both the Security Group rules attached to the instance and the NACL rules attached to the subnet.

---

## 4. ICMP and Diagnostic Rules

To allow ping diagnostics (`ping` command) for network latency monitoring:
* Add an Inbound Rule: Protocol: `ICMP`, Type: `Echo Request` (Type 8), Code: `0`, Source: Authorized diagnostic subnet or monitoring server IP.
* Ensure outbound ICMP Echo Reply (Type 0) is permitted if strict egress filtering is enabled.

---

## 5. Security Best Practices and Rule Auditing

* **Principle of Least Privilege**: Never open management ports (22, 3389, 2376) to `0.0.0.0/0`.
* **Group Chaining**: Reference security groups as sources instead of hardcoding IP addresses within multi-tier cloud applications.
* **Unused Rule Pruning**: Regularly audit and delete stale security group rules during maintenance cycles to avoid accidental exposure.
