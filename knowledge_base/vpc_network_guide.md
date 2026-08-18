---
title: "NovaCloud VPC Architecture and Networking Guide"
visibility: "PUBLIC"
category: "networking"
---

# NovaCloud VPC Architecture and Networking Guide

A NovaCloud Virtual Private Cloud (VPC) is a logically isolated virtual network dedicated to your cloud account. It enables you to provision compute, database, and storage resources in a secure, customizable network environment.

---

## 1. VPC CIDR Blocks and Subnet Partitioning

* **VPC CIDR Allocation**: When creating a VPC, select a private RFC 1918 IPv4 block (e.g., `10.0.0.0/16`, `172.16.0.0/16`, or `192.168.0.0/16`).
* **Subnet Slicing**: Divide the VPC CIDR block into smaller subnets across availability zones (e.g., `10.0.1.0/24` for Public Subnet A, `10.0.2.0/24` for Private Subnet A).
* **Reserved Addresses**: NovaCloud reserves the first four IP addresses and the last IP address in every subnet for network routing, DHCP, internal DNS resolver, and broadcast.

---

## 2. Public Subnets vs. Private Subnets

NovaCloud subnets are classified based on their routing table associations:
* **Public Subnet**:
  * Associated route table contains a default route (`0.0.0.0/0`) targeting a NovaCloud **Internet Gateway (IGW)**.
  * Instances in public subnets can be assigned public IPv4 addresses and communicate directly with the internet.
* **Private Subnet**:
  * Route table does not target an Internet Gateway.
  * Instances communicate strictly within the VPC or outbound through a **NAT Gateway**.

---

## 3. Internet Gateways and NAT Gateways

* **Internet Gateway (IGW)**: Horizontally scaled, redundant VPC component that enables bidirectional communication between public subnet instances and the internet.
* **NAT Gateway**: Deployed in a *public* subnet to provide outbound internet connectivity for instances in *private* subnets (e.g., for operating system package updates) without exposing them to inbound internet connections.
* **Route Configuration for NAT**:
  * In the private subnet route table, add destination `0.0.0.0/0` with target set to the NAT Gateway ID (`nat-xxxxxx`).

---

## 4. VPC Peering and Inter-VPC Connectivity

* **VPC Peering Connection**: Connects two NovaCloud VPCs to route traffic between them using private IPv4 addresses.
* **Non-Overlapping CIDRs**: VPC peering requires that the two VPCs do not have overlapping CIDR address spaces (e.g., `10.0.0.0/16` and `10.1.0.0/16`).
* **Non-Transitive Routing**: VPC peering relationships are strictly point-to-point. Traffic cannot traverse through an intermediate VPC to reach a third VPC.
* **Route Table Updates**: After establishing a peering link, add routes in both VPC route tables directing the peer VPC CIDR to the peering connection ID (`pcx-xxxxxx`).

---

## 5. Network Troubleshooting Checklist

If instances in a VPC cannot establish network communication:
1. **Route Table Targets**: Ensure the instance subnet has an active route table with valid next-hop targets (IGW, NAT Gateway, or Peering Connection).
2. **Security Groups & NACLs**: Check for rule conflicts or missing permit entries.
3. **IP Conflicts**: Verify no duplicate static IP assignments exist within the subnet DHCP range.
