# Integration Service Overview

## Definition

The **Integration Service** acts as a **middleware layer** enabling back-end communication between the **EJAR Platform** and the **Saudi Electricity Company (SEC)**.

## Objective

- Ensure there are **no outstanding balances or account receivables** on any **Contract Account** linked to an active rental relation within EJAR.
- Maintain financial and operational consistency between EJAR’s tenancy records and SEC’s electricity accounts.

## Roles

| Role | Entity | Description |
|------|---------|-------------|
| **Service Provider** | SEC (Saudi Electricity Company) | Provides and maintains integration APIs for electricity service management. |
| **Service Requester** | EJAR Platform | Consumes and triggers SEC’s API services to manage tenancy-related electricity transfers. |

## Context

These functions are **critical for managing electricity service liability** between the **lessor (owner)** and **tenant** throughout the contract lifecycle.

---

# SEC Integration — List of Services (APIs)

The EJAR Platform consumes **six REST API operations** from SEC through the Integration Service.

| Operation ID | Name | Function |
|---------------|------|-----------|
| `SEC_OP_1` | Premise Check | Validates premise and meter details |
| `SEC_OP_2` | Tenant Stumble Check | Checks tenant financial eligibility |
| `SEC_OP_3` | Meter Reading Plausibility Check | Validates meter readings during handover |
| `SEC_OP_4` | Tenant Move-In | Transfers liability from lessor to tenant |
| `SEC_OP_5` | Tenant Move-Out | Transfers liability back to lessor |
| `SEC_OP_6` | Ejar Notification | Keeps SEC records synchronized with EJAR |

---

# SEC_OP_1 — Premise Check

## Purpose

To verify and validate **premise details** before initiating any electricity-related process in EJAR.

## Function

- Confirms **Premise ID**, **meter number**, and **national address**.
- Validates **owner and tenant details** for approved residential and commercial usage categories.

## Limitation

- Current implementation supports **single-meter installations only**.

---

# SEC_OP_2 — Tenant Stumble Check

## Purpose

To check the **tenant’s financial eligibility** before starting a new rental contract.

## Function

- Retrieves financial standing and “stumble” status from SEC’s **SAP IS-U** system.
- Verifies if the tenant has any **unpaid dues or obstacles** in previous contracts.

## Key Output

- `TotalDueBalance`: Total outstanding balance across all associated accounts.
- `ContractAccounts`: List of SEC Contract Accounts tied to the tenant’s **National ID**.

---

# SEC_OP_3 — Meter Reading Plausibility Check

## Purpose

To ensure **accuracy of meter readings** during contract handover.

## Function

- Validates **meter readings** supplied by tenants or lessors.
- Applicable only to **non-smart (dumb) meters**.

## Plausibility Result

- If the reading is **implausible or missing**, SEC returns an **expected reading** value.
- Helps prevent data entry errors or fraudulent meter reports.

## EJAR Requirement

EJAR must invoke this API during:

- **Tenant Move-In (MI)**
- **Tenant Move-Out (MO)**  
to verify the plausibility of the submitted readings.

---

# SEC_OP_4 — Tenant Move-In

## Purpose

To **transfer electricity service liability** from the **lessor** to the **tenant** at the start of a tenancy.

## Function

- Updates SEC’s **SAP IS-U** system to assign billing and consumption responsibility to the tenant.

## Trigger

- Automatically initiated during:
  - **Contract issuance**
  - **Contract re-issuance**
  - **Liability transfer events** for existing contracts.

## Output

- Returns a **Reference Number** from SEC’s SAP IS-U system representing the Move-In transaction.

---

# SEC_OP_5 — Tenant Move-Out

## Purpose

To end the tenant’s electricity liability when a contract expires, is terminated, or upon explicit request.

## Function

- Transfers electricity service responsibility **back to the owner/lessor** in SEC’s system.

## Trigger

- Triggered by EJAR during:
  - **Contract termination**
  - **Contract expiry**
  - **On-demand Move-Out request**

## Constraint

- Can only be initiated for contracts where the **Move-In request was originally processed through EJAR**.

---

# SEC_OP_6 — Ejar Notification

## Purpose

To keep SEC’s internal records aligned with EJAR’s contract updates and ownership changes.

## Function

- Sends **notifications** to SEC about any changes in tenancy or ownership details.

## Supported Update Events

| Code | Description |
|------|--------------|
| `BR001` | Change Owner |
| `BR002` | Change Lessor (representative) |
| `BR003` | Change Owner/Lessor |
| `BR005` | Contract Renewal |

---

# Summary of EJAR–SEC Integration Logic

| Aspect | Description |
|--------|--------------|
| **Middleware** | Integration Service (EJAR–SEC connector) |
| **System Roles** | SEC → Provider, EJAR → Consumer |
| **Objective** | Ensure no outstanding balance & proper liability handover |
| **Total APIs** | Six main SEC operations integrated |
| **Core Functions** | Validation, Eligibility, Meter Reading, Liability Transfer, Notifications |
