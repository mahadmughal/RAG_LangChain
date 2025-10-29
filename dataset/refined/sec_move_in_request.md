---
doc_id: move_in_request_overview_v1
title: Move-In (MI) Request — Overview
version: 1.0
domain: ejar-sec
language: en
tags: [ejar, sec, move-in, validation, tenant, premise, account, workflow]
entities:
  operation: move_in
  apis: [AccountCheck, TenantStumbleCheck, MoveIn]
  endpoints: [POST /mi/check]
errors:
  sec: [E302, E303, E101, E103]
  validation: [ContractNotFound, ContractWasArchived, ContractWasExpired, ContractWasTerminated, ContractWasRevoked, TenantAlreadyUsed, TenantMismatch, PremiseIdAlreadyUsed, MissingAccountNo, InvalidAccountNoLength, PendingRidRequestExists, FixedAmount]
aliases:
  contract_account: [contract account, CA, رقم الحساب]
  premise_id: [premise id, PremiseID, رقم الموقع]
  move_in: [move in, MI, نقل الذمة للمستأجر]
  move_out: [move out, MO, نقل الذمة للمالك]
  sublease: [sub-lease, من الباطن]
---

# Move-In (MI) Request — Overview

## Overview of Move-In Request Process

**Purpose:** Describes the overall objective of the Move-In (MI) Request process in the EJAR–SEC integration system.  
**Logic Flow:**

- The tenant or property manager triggers `POST /mi/check` to verify if electricity can be transferred.
- System validates inputs, retrieves contract & property info, and performs SEC verifications.
- When checks pass, a **pending** Move-In request record is created and processed asynchronously.
- Ensures electricity account transfer aligns with EJAR contract validity.  
**Dependencies:** EJAR Core API, SEC.AccountCheck, SEC.TenantStumbleCheck  
**Output:** A validated, pending Move-In record awaiting SEC execution.

---

# Validation & Processing Steps

## Step 1: Pending Request Cleanup

**Purpose:** Prevent duplicate Move-In requests for the same contract & unit.  
**Logic Flow:**

- Search existing pending MI for same `contract_number` + `unit_number`.
- Delete duplicates to keep one active request per pair.  
**Business Rules:** Only one pending move-in per contract–unit.  
**Dependencies:** App::Model::SecRequestRepository  
**Code:**

```ruby
mi_requests = request_repository.index(filters: {
  contract_number: param_attributes[:contract_number],
  unit_number: param_attributes[:unit_number],
  request_type: 'move_in',
  status__in: [SEC_REQUEST_STATUS[:pending]]
})
mi_requests.each { |req| request_repository.delete(req.id) }
```

## Step 2: Account Number Validation

**Purpose:** Ensure account number presence & format.  
**Logic Flow:**

- If blank → `MissingAccountNo`.
- If not 11 digits or not 12 digits starting with `0` → `InvalidAccountNoLength`.  
**Business Rules:** Valid formats: 11 digits OR 12 digits starting with `0`.  
**Dependencies:** App::Services::Validation::AccountNoValidation  
**Code:** `App::Services::Validation::AccountNoValidation.validate(account_no: account_no)`

## Step 3: Contract Retrieval

**Purpose:** Fetch contract from EJAR Core before proceeding.  
**Logic Flow:**

- Call `fetch_and_store_contract_from_core_application(param_attributes)`.
- Retrieve contract id, type, parties, duration, services.
- If not found → `ContractNotFound`.  
**Dependencies:** EJAR Core API  
**Output:** Contract object for further validation & SEC calls.

## Step 4: Contract Validation

**Purpose:** Comprehensive eligibility checks.  
**Logic Flow:**  

- Contract exists; not AWQAF or sublease; residential/commercial.  
- Duration > 3 months.  
- State not archived/terminated/expired/revoked; conditional → active.  
- Parties verified (lessor, tenant).  
- No duplicate approved MI without corresponding MO.  
- No fixed-fee electricity; no pending RID.  
**Business Rules:** Block invalid states; ensure one active MI unless MO exists.  
**Errors:** AwqafNotAllowed, SubleaseNotAllowed, ContractTypeNotSupported, ContractLessThreeMonths, ContractWasArchived, ContractWasTerminated, ContractWasExpired, ContractWasRevoked, ConditionalNotAllowed, MissingParty, MissingLessor, MissingTenant, InvalidIdType, PartyNotVerified, LessorOrganizationMissingInfo, TenantOrganizationMissingInfo, AlreadyHadMi, FixedAmount, PendingRidRequestExists  
**Dependencies:** App::Services::Validation::ContractValidation, `Ejar3::Api.contract.pending_requests`  
**Code:** `validate_contract(contract, settings, auth_context, param_attributes)`

## Step 5: SEC AccountCheck API

**Purpose:** Retrieve premise & meter details by account number.  
**Logic Flow:**

- Call `SEC.AccountCheck`.  
- Extract `PremiseID`, `MeterNumber`, `EquipmentNumber`, `MeterType`, `SiteScenario`, `OutstandingBalance`.  
- Store in MI context.  
- On `E302`/`E303`/`E101`/`E103` → stop.  
**Dependencies:** SEC API Gateway, ExternalCalls::Model::CallRepository  
**Sample Response (trimmed):**

```json
{
  "PremiseID": "4008462968",
  "SiteScenario": "SN",
  "MCCCIndicator": "1",
  "OutstandingBalanceofPremise": "0.00",
  "MeterDetails": {"MeterNumber": "12345678","EquipmentNumber":"33459941","MeterType":"1"},
  "TenantDetails": {"IndividualDetails": {"IDNumber": "1234567890","IDType": "ZNID"}}
}
```

## Step 6: Premise Validation

**Purpose:** Ensure the premise isn’t already linked to another active MI.  
**Logic Flow:**

- Find MI with same `premise_id` and statuses `[to_be_transferred, waiting_parties, approved, transferred]`.  
- Filter out same contract/unit.  
- If remaining has no approved MO → `PremiseIdAlreadyUsed`.  
**Business Rules:** One active contract per premise.  
**Dependencies:** App::Services::Validation::PremiseCheckValidation  
**Code:** `PremiseCheckValidation.validate(premise_id: premise_id, contract: contract, unit_number: param_attributes[:unit_number])`

## Step 7: SEC TenantStumbleCheck API

**Purpose:** Verify tenant identity & validity.  
**Logic Flow:**

- Call `SEC.TenantStumbleCheck` with tenant ID & type.  
- Store external call id; check result; handle `E103`/`TenantMismatch`.  
**Dependencies:** SEC API Gateway  
**Sample Response (trimmed):**

```json
{"EJARTenantStumbleCheckResponse":{"IDNumber":"1234567890","IDType":"ZNID","Result":{"MessageCode":"S","MessageText":"Successful"}}}
```

## Step 8: Tenant Validation

**Purpose:** Avoid multiple active MIs for same tenant (unless MO exists).  
**Logic Flow:**  

- Blank tenant id → skip.  
- If ID starts with `1` (Saudi national) → auto-pass.  
- Else, search contracts by same tenant id; MI without MO → `TenantAlreadyUsed`.  
**Business Rules:** One active MI per tenant unless MO recorded. Saudi nationals exempt.  
**Dependencies:** App::Services::Validation::TenantCheckValidation  
**Code:** `TenantCheckValidation.validate(tenant_id_number: tenant_id_number, contract: contract)`

## Step 9: Move-In Request Creation

**Purpose:** Create MI after validations pass.  
**Logic Flow:**  

- Combine contract + AccountCheck + TenantStumbleCheck.  
- Generate `request_number` via `App::Utils::Token.unique_human_readable_token`.  
- Set `status='pending'`; persist; trigger `SEC.MoveIn` job.  
**Code (shape):**

```ruby
{ contract_number: ..., account_no: ..., premise_id: ...,
  tenant_id_number: ..., status: SEC_REQUEST_STATUS[:pending] }
```

**Output:** Pending MI with tenant, meter, and premise data.

## Step 10: Background Job Execution

**Purpose:** Execute actual `SEC.MoveIn` asynchronously.  
**Logic Flow:**  

- Worker polls pending MIs.  
- Calls `SEC.MoveIn` with gathered params.  
- Updates status (approved/failed); syncs meter/premise info in EJAR.  
**Dependencies:** Background Job Worker, SEC.MoveIn API  
**Errors:** External call failure, Timeout, API response error

---

# Error Taxonomy

**SEC Errors:** `E302` Invalid Contract Account Number; `E303` No Active Property; `E101` Invalid Premise; `E103` Invalid ID Number.  
**Validation Errors:**  

- **Contract:** ContractNotFound, ContractWasArchived, ContractWasExpired, ContractWasTerminated, ContractWasRevoked  
- **Tenant:** TenantAlreadyUsed, TenantMismatch  
- **Premise:** PremiseIdAlreadyUsed  
- **Account:** MissingAccountNo, InvalidAccountNoLength  
- **RID:** PendingRidRequestExists  
- **FeeType:** FixedAmount

---

# Design Principles Summary

- Strict idempotency.  
- Two-phase flow (eligibility → SEC execution).  
- Encapsulated validation classes.  
- Separate internal vs external validations.  
- Comprehensive audit logging.

---

## Synonyms & Arabic Terms (for search)

- Contract Account = CA, رقم الحساب
- Premise ID = PremiseID, رقم الموقع
- Move-In = MI, نقل الذمة للمستأجر
- Move-Out = MO, نقل الذمة للمالك
- Sublease = من الباطن

## FAQ (Developer)

**Q:** What stops the flow at AccountCheck?  
**A:** SEC returns `E302/E303/E101/E103`. The MI flow halts and surfaces the mapped error.

**Q:** When does `PremiseIdAlreadyUsed` occur?  
**A:** There’s an MI for the same `premise_id` in states `[to_be_transferred, waiting_parties, approved, transferred]` without a corresponding approved MO.

**Q:** Why are Saudi nationals sometimes “auto-pass” in tenant validation?  
**A:** IDs starting with `1` (nationals) can be flagged as auto-pass per business rule; non-nationals require cross-contract checks for prior MI without MO.

**Q:** Which SEC Ops map to these steps?  
**A:** Step 5 → **SEC_OP_1 AccountCheck**; Step 7 → **SEC_OP_2 TenantStumbleCheck**; Step 10 concludes with **SEC_OP_4 Move-In** execution.
