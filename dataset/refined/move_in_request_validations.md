---
doc_id: internal_validations_move_in_v1
title: Internal EJAR Validations — Move-In
version: 1.0
domain: ejar-sec
language: en
tags: [ejar, sec, move-in, validation, tenant, premise, account]
entities:
  operation: move_in
  apis: [AccountCheck, TenantStumbleCheck, MoveIn]
  states_invalid: [rejected, archived, terminated, expired, revoked]
errors: [ContractNotFound, PendingRidRequestExists, FixedAmount, AwqafNotAllowed, SubleaseNotAllowed, ContractTypeNotSupported, ContractLessThreeMonths, ContractWasRejected, ContractWasArchived, ContractWasTerminated, ContractWasExpired, ContractWasRevoked, ConditionalNotAllowed, MissingParty, MissingLessor, MissingTenant, InvalidIdType, PartyNotVerified, LessorOrganizationMissingInfo, TenantOrganizationMissingInfo, InvalidContractAccountNumber, PremiseIdAlreadyUsed, TenantStumbleCheckFailed, MissingPremiseId, InvalidPremiseId, MissingAccountNo, InvalidAccountNoLength]
aliases:
  contract_account: [contract account, CA, رقم الحساب]
  premise_id: [premise id, PremiseID, رقم الموقع]
  move_in: [move in, MI, نقل الذمة للمستأجر]
  move_out: [move out, MO, نقل الذمة للمالك]
  sublease: [sub-lease, من الباطن]
---

# Internal EJAR Validations — Move-In Request

## Overview

The **Internal EJAR Validations** define the complete pre-check process that ensures data integrity, contract eligibility, and compliance before initiating a **Tenant Move-In (MI)** request in the EJAR–SEC integration.  
These validations occur internally before SEC APIs are called.

---

## Step 1 — Account Number Validation

### Purpose

Ensure that the **Contract Account Number** is present and correctly formatted.

### Rules

- If `account_no` is blank → `MissingAccountNo`.
- If not 11 digits or 12 digits starting with `0` → `InvalidAccountNoLength`.
- Must contain only digits (`\d+`).

### Example

```ruby
App::Services::Validation::AccountNoValidation.validate(account_no: account_no)
```

---

## Step 2 — Parameter Validation

### Purpose

Validate core parameters required for SEC communication.

### Rules

```ruby
raise MissingPremiseId if premise_id.blank?
raise InvalidPremiseId if premise_id.to_s.length != 10
raise InvalidPremiseId unless premise_id.to_s.scan(/\D/).empty?
```

If any of these conditions fail, the request is rejected.

---

## Step 3 — Contract Retrieval Check

### Purpose

Ensure that the contract exists in the **EJAR Core Application** before proceeding.

### Rules

- Fetch contract from ejar3-core-application repository.
- If not found → `raise ContractNotFound`.

---

## Step 4 — Pending RID Request Validation

### Purpose

Prevent new Move-In requests when a **pending RID request** already exists for an active contract.

### Rule

```ruby
raise PendingRidRequestExists if contract.active? && pending_rid?
```

---

## Step 5 — Fixed Fee Check

### Purpose

Ensure that none of the **contract_unit_services** have a fixed fee type.

### Rule

If any service has `fixed_fee`, the process is halted:

```ruby
raise FixedAmount if is_fixed_amount
```

---

## Step 6 — Contract-Level Validations

### Purpose

Verify that the contract meets all eligibility criteria for SEC integration.

### 6.1 — AWQAF (Endowment) Exclusion

- Endowment contracts are **not eligible**.

```ruby
raise AwqafNotAllowed if contract.is_awqaf
```

### 6.2 — Sublease Restriction

- Sublease contracts cannot trigger Move-In.

```ruby
raise SubleaseNotAllowed if contract.contract_sub_type == 'sublease'
```

### 6.3 — Supported Contract Types

- Only `residential` and `commercial` are supported.

```ruby
raise ContractTypeNotSupported unless contract.contract_type.in?(%w[residential commercial])
```

### 6.4 — Minimum Duration

- Duration must be **≥ 3 months**.

```ruby
raise ContractLessThreeMonths if contract.less_than_3_months_period?
```

### 6.5 — Invalid States

Contracts in these states cannot proceed:

| State | Error |
|--------|--------|
| rejected | ContractWasRejected |
| archived | ContractWasArchived |
| terminated | ContractWasTerminated |
| expired | ContractWasExpired |
| revoked | ContractWasRevoked |

### 6.6 — Conditional Contracts

Conditional contracts must be **active** to qualify.

```ruby
raise ConditionalNotAllowed if contract.is_conditional_contract && !contract.state.in?(%w[active])
```

---

## Step 7 — Contract Parties Validation

### Purpose

Ensure that the contract includes valid and verified parties.

### Rules

1. Contract must include at least one **lessor** and one **tenant**.
2. **Individual Parties**
   - `id_type` must be among allowed values.
   - `verification_status` must be one of `verification_succeed` or `contract_ready`.
3. **Organizations**
   - Must include `cr_legal_type_id` for both lessor and tenant.

### Possible Errors

`MissingParty`, `MissingLessor`, `MissingTenant`, `InvalidIdType`, `PartyNotVerified`, `LessorOrganizationMissingInfo`, `TenantOrganizationMissingInfo`

---

## Step 8 — SEC Account Validation

### Purpose

Verify that the contract account number is valid via **SEC.AccountCheck** API.

### Rule

If SEC returns invalid account or premise → `InvalidContractAccountNumber`.

---

## Step 9 — Premise ID Validation

### Purpose

Ensure the **Premise ID** is not already used by another active Move-In.

### Rule

If there exists a pending or approved Move-In with no Move-Out → `PremiseIdAlreadyUsed`.

---

## Step 10 — Tenant Stumble Check

### Purpose

Validate the tenant’s financial and eligibility status via **SEC.TenantStumbleCheck** API.

### Outcome

If the tenant is blocked, stumbled, or owes dues → process halted.

---

## Step 11 — Finalization

### Purpose

Once all validations succeed:

- Create the Move-In request.
- Assign a unique SEC reference number.
- Set status to `pending` until SEC confirms completion.

---

## Validation Summary Table

| Step | Validation | Error |
|------|-------------|--------|
| 1 | Account Number Validation | MissingAccountNo, InvalidAccountNoLength |
| 2 | Premise ID Validation | MissingPremiseId, InvalidPremiseId |
| 3 | Contract Retrieval | ContractNotFound |
| 4 | Pending RID | PendingRidRequestExists |
| 5 | Fixed Fee Check | FixedAmount |
| 6 | Contract Rules | AwqafNotAllowed, SubleaseNotAllowed, ContractTypeNotSupported, ContractLessThreeMonths, ContractWasRejected, ContractWasArchived, ContractWasTerminated, ContractWasExpired, ContractWasRevoked, ConditionalNotAllowed |
| 7 | Contract Parties | MissingParty, InvalidIdType, PartyNotVerified |
| 8 | SEC Account Check | InvalidContractAccountNumber |
| 9 | Premise Reuse | PremiseIdAlreadyUsed |
| 10 | Tenant Validation | TenantStumbleCheckFailed |

---

## Keywords

`EJAR`, `SEC`, `Move-In`, `Validation`, `Contract`, `Premise ID`, `AccountCheck`, `TenantStumbleCheck`, `RID`, `Fixed Fee`, `EJAR Core Application`

---

## Synonyms & Arabic Terms (for search)

- Contract Account = CA, رقم الحساب
- Premise ID = PremiseID, رقم الموقع
- Move-In = MI, نقل الذمة للمستأجر
- Move-Out = MO, نقل الذمة للمالك
- Sublease = من الباطن

## FAQ (Developer)

**Q:** Why would `PremiseIdAlreadyUsed` trigger?  
**A:** There’s an existing MI for the same premise without an approved MO.

**Q:** Can sublease contracts proceed with MI?  
**A:** No. `SubleaseNotAllowed`.

**Q:** Which SEC-provided APIs are involved in the process of creating/initiating MI request?  
**A:** `AccountCheck` (SEC_OP_1) validates account/premise; `TenantStumbleCheck` (SEC_OP_2) validates tenant; successful validations lead to `Move-In` execution (SEC_OP_4).
