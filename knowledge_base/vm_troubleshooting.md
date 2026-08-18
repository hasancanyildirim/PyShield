---
title: "NovaCloud Virtual Machine Troubleshooting Guide"
visibility: "PUBLIC"
category: "compute"
---

# NovaCloud Virtual Machine Troubleshooting Guide

This guide provides step-by-step diagnostic and remediation workflows for resolving common compute instance and virtual machine (VM) issues hosted on the NovaCloud platform.

---

## 1. VM Lifecycle States and Diagnostics

NovaCloud compute instances transition through several defined lifecycle states:
* **PROVISIONING**: The hypervisor is allocating vCPU, RAM, and attached block storage volumes.
* **RUNNING**: The guest operating system kernel is active and responding to hypervisor heartbeats.
* **STOPPED**: The instance has been gracefully shut down or stopped via the NovaCloud Management Console.
* **ERROR**: An underlying hypervisor fault, storage detachment, or invalid configuration prevented normal execution.

### Resolving the ERROR State
If your virtual machine enters the `ERROR` state during boot:
1. Navigate to the **NovaCloud Console > Compute > Instances**.
2. Select the affected instance and review the **System Activity Log**.
3. Perform a **Hard Reboot** (Power Cycle) via the console actions menu.
4. If the error persists, detach the root system volume and attach it to a temporary rescue instance to inspect system journal logs (`/var/log/syslog` or Windows Event Viewer).

---

## 2. Kernel Panic and Boot Failure Recovery

Bootloader corruption or kernel panics typically manifest as instances becoming unresponsive during startup:
* **Serial Console Access**: Use the **NovaCloud Interactive Serial Console** to inspect real-time boot messages and GRUB menu options.
* **Emergency Mode / Single-User Mode**: Reboot the instance through the serial console, select advanced boot options in GRUB, and append `systemd.unit=emergency.target` to repair disk filesystems using `fsck`.
* **Kernel Rollback**: If a kernel update caused boot failure, select the previous stable kernel entry from the GRUB boot menu and update `/etc/default/grub`.

---

## 3. High Resource Utilization (CPU, Memory, Disk I/O)

Performance degradation often stems from resource contention inside the guest OS:
* **CPU Throttling**: Inspect running processes using `top`, `htop`, or Windows Task Manager. If continuous CPU utilization exceeds 90%, consider upgrading to a higher vCPU tier (e.g., from `nc.c1.medium` to `nc.c1.large`).
* **Out of Memory (OOM) Killer**: Check kernel logs (`dmesg -T | grep -i oom`) to identify processes terminated due to memory exhaustion. Enable or expand swap space on high-memory workloads.
* **Disk I/O Latency**: Check storage IOPS metrics in the NovaCloud Monitoring Dashboard. Ensure attached SSD storage volumes match required throughput baselines.

---

## 4. SSH and Remote Access Troubleshooting

When unable to connect to your instance via SSH (Port 22) or RDP (Port 3389):
* **Security Group Ingress**: Verify that your Security Group includes an inbound rule allowing TCP traffic on your management port from your client public IP.
* **SSH Key Pair Verification**: Ensure you are connecting with the correct private key (`ssh -i key.pem user@vm-public-ip`) and that file permissions on the private key are restricted (`chmod 400 key.pem`).
* **Guest Firewall Conflicts**: Ensure local software firewalls (such as `ufw`, `iptables`, or Windows Defender Firewall) are not blocking incoming management connections.

---

## 5. Storage Volume and Disk Resizing

When system disks run out of capacity:
1. In the NovaCloud Console, navigate to **Volumes** and select **Extend Volume**.
2. Allocate the desired disk capacity.
3. Inside the guest OS, expand the partition and filesystem:
   * **Linux ext4**: Run `growpart /dev/vda 1` followed by `resize2fs /dev/vda1`.
   * **Linux xfs**: Run `xfs_growfs /`.
   * **Windows**: Open Disk Management (`diskmgmt.msc`) and select **Extend Volume**.
