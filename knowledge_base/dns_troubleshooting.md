---
title: "NovaCloud DNS and Domain Resolution Troubleshooting Guide"
visibility: "PUBLIC"
category: "networking"
---

# NovaCloud DNS and Domain Resolution Troubleshooting Guide

NovaCloud DNS provides high-availability authoritative domain hosting and internal private DNS resolution within Virtual Private Clouds (VPC). This guide covers standard diagnostic commands, common record configurations, and troubleshooting steps for domain resolution issues.

---

## 1. Supported DNS Record Types and Configurations

NovaCloud Authoritative DNS supports standard RFC-compliant record types:
* **A Record**: Maps a fully qualified domain name (FQDN) to an IPv4 address (e.g., `app.example.com` -> `198.51.100.25`).
* **AAAA Record**: Maps an FQDN to an IPv6 address.
* **CNAME Record**: Aliases one canonical domain name to another (e.g., `www.example.com` -> `example.com`). Note: CNAME cannot coexist with other record types at the zone apex (`@`).
* **MX Record**: Specifies mail exchange servers for email routing with integer priority values (e.g., Priority `10`, Target `mail.example.com`).
* **TXT Record**: Holds arbitrary text data, typically utilized for domain verification, SPF (`v=spf1 ...`), DKIM, and DMARC email security policies.

---

## 2. Common DNS Error Codes and Causes

* **NXDOMAIN (Non-Existent Domain)**:
  * Indicates the queried domain name does not exist within the authoritative zone.
  * *Resolution*: Check for typographical errors in the DNS record name and ensure the domain registration is active.
* **SERVFAIL (Server Failure)**:
  * Indicates the recursive resolver could not obtain an authoritative answer, often due to DNSSEC validation failure or misconfigured nameserver delegation at the registrar.
  * *Resolution*: Validate parent registrar NS records and check DNSSEC DS record key fingerprints.
* **REFUSED**:
  * Indicates the nameserver refused to process the request due to access control list policies (e.g., recursive queries directed at an authoritative-only server).

---

## 3. Diagnostic Commands Reference

Use standard command-line tools to diagnose DNS resolution:

### Using `nslookup`
* Check A record resolution: `nslookup app.example.com`
* Query specific nameserver directly: `nslookup app.example.com ns1.novacloud-dns.com`

### Using `dig` (Domain Information Groper)
* Detailed query with trace: `dig +trace +nocmd app.example.com any +multiline`
* Query MX records: `dig example.com MX +short`
* Check authoritative SOA serial numbers: `dig example.com SOA`

---

## 4. Understanding TTL and Propagation Latency

* **Time to Live (TTL)**: Defines the duration in seconds that intermediate recursive resolvers and client operating systems cache DNS query responses.
* **Propagation Latency**: When updating DNS records, changes take up to the previous TTL duration to propagate globally across all recursive resolvers.
* **Pre-Migration Best Practice**: Lower record TTL values to `300` seconds (5 minutes) at least 24 hours prior to scheduled server migrations to minimize DNS caching delays.

---

## 5. NovaCloud Private DNS Zones in VPCs

* **Internal FQDN Resolution**: Private DNS zones allow resolution of custom domain names (e.g., `db.internal.novacloud`) strictly within designated VPC subnets.
* **VPC Resolver Endpoint**: Ensure VPC DHCP options are set to use the NovaCloud Default VPC DNS Resolver (`10.0.0.2` or base network `+2` offset).
* **Split-Horizon DNS**: Used when public clients require public IP resolution while internal VMs query private IP addresses for the same FQDN.
