# Saudi Electricity Company (SEC) — Role in EJAR Integration

## Overview

The **Saudi Electricity Company (SEC)** is the primary entity responsible for **utility management** and **electricity service provision** within the EJAR ecosystem.

SEC provides the **technical infrastructure**, **billing systems**, and **data services** that connect electricity usage with tenancy contracts managed through the EJAR platform.

---

# Role of SEC in the EJAR System

## Service Provider Role

- Within the EJAR ecosystem, **SEC acts as the Service Provider**.
- SEC provides and maintains the **Integration Service**, which links **utility liability** to **rental contracts**.
- The integration ensures that electricity services are properly assigned between **lessors** and **tenants** based on the contract lifecycle.

---

# Core Function — Utility Management

## System Used

SEC manages all utility operations using **SAP IS-U** (SAP’s Industry-Specific Solution for the Utilities Industry).

## Supported Business Functions

The SAP IS-U system enables SEC to:

- Record and manage **meter readings**.
- Generate and issue **electricity bills and invoices**.
- Handle **payment processing** and **accounting records**.
- Manage **customer service requests** and **disconnection/reconnection workflows**.

## Objective

To ensure **accurate, traceable, and timely utility billing** that reflects the active tenancy status within EJAR.

---

# Customer Definition in SEC

## Who is a Customer?

A **Customer** in SEC is defined as the **beneficiary receiving electricity services through an active electricity meter**.

## Relation to EJAR

- Every EJAR contract involves at least one active **SEC Customer Account** if that contract has electricity unit service enabled.
- This account determines **who is financially liable** for electricity consumption during the contract period.

---

# EJAR–SEC Integration Overview

## EJAR’s Role

- The **EJAR Platform** (operated by the **Ministry of Housing — MOH**) regulates and manages **tenancy and leasing** activities in the Saudi real estate market.
- EJAR functions as the **Service Requester**.
- It consumes and triggers **SEC’s integration APIs** through the **Integration Service** layer.

## Integration Service Function

- Acts as a **middleware layer** that connects EJAR and SEC systems.
- Handles all **back-end API communication** related to:
  - Premise and meter validation.
  - Tenant eligibility checks.
  - Electricity liability transfers.

## Integration Goal

- To manage the **transfer of electricity service liability** between **lessor** and **tenant**.
- To ensure there are **no outstanding receivables or unpaid balances** linked to any contract account during an active tenancy.

---

# Key Operations for Electricity Liability Transfer

SEC provides two **core API operations** that enable the transfer of liability between the **owner/lessor** and the **tenant**:

---

## Tenant Move-In (MI)

### Purpose

Transfers electricity service liability **from the owner/lessor to the tenant** at the start of a valid rental contract.

### System Function

- Executed through **SEC’s SAP IS-U** system.
- When processed successfully:
  - **New bills** are issued under the **tenant’s name**.
  - The tenant becomes the **liable consumer** for all electricity usage and charges.

### Trigger

- Initiated by EJAR when:
  - A new **rental contract is issued or reissued**.
  - An existing contract undergoes a **Move-In update** due to change in tenancy.

---

## Tenant Move-Out (MO)

### Purpose

Transfers electricity service liability **back to the owner/lessor** when a tenancy ends.

### Function

- Triggered by EJAR when:
  - The contract is **expired**, **terminated**, **revoked**, **archived**, or a **Move-Out request** is manually initiated.

### System Behavior

- SEC’s system issues a **final electricity bill** to the outgoing tenant.
- After payment, financial liability is reassigned to the **owner/lessor**.

### Constraint

- The Move-Out process can only be executed if the **corresponding Move-In** was originally initiated by EJAR.

---

# Summary: Roles and Integration Logic

| Aspect | Description |
|--------|--------------|
| **System Provider** | Saudi Electricity Company (SEC) |
| **System Requester** | EJAR Platform (Ministry of Housing) |
| **Middleware** | Integration Service (EJAR ↔ SEC connector) |
| **Primary Objective** | Manage electricity liability transfer between lessor and tenant |
| **System Backbone** | SAP IS-U — manages meters, billing, invoicing, and customers |
| **Core Operations** | Tenant Move-In (MI), Tenant Move-Out (MO) |
| **Customer Definition** | Beneficiary who receives SEC services through an electricity meter |

---

# Key Insights

- **SEC = Utility Management & Billing System.**
- **EJAR = Tenancy Regulation & Contract Management.**
- Integration ensures that **electricity liability** mirrors **contractual responsibility** in real time.
- The **Move-In / Move-Out operations** are the foundation of this liability management process.
