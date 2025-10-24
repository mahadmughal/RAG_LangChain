The Saudi Electricity Company (SEC) is the entity responsible for utility management and service provision within this context.

Role as Service Provider: Within the EJAR system, SEC functions as the Service Provider. This means SEC provides and maintains the underlying integration service that connects utility liability to the rental contracts managed by EJAR.

Core Function (Utility Management): SEC manages utility services and information using SAP IS-U (SAP’s Industry-Specific Solution for the Utilities Industry). This system supports all critical business functions related to electricity delivery, including meter reading, billing, invoicing, accounting, and customer service.

Customer Definition: A Customer in SEC is defined as the beneficiary who receives SEC services through an electricity meter.

The EJAR platform (a comprehensive and integrated system run by the Ministry of Housing—MOH) regulates tenancy. It is linked to SEC to regulate and control the tenancy and leasing in the real-estate market.

The primary mechanism for this link is the Integration Service, which acts as a middle-ware layer serving back-end integration between the two platforms.

EJAR's Role: EJAR acts as the Service Requester that consumes the functions (operations) provided by SEC.

Integration Goal: The objective is to manage the transferring of electricity service liability between the owner/lessor and the tenant during the contract duration. This also ensures that there are no outstanding account receivables or outstanding items associated with the SEC customer involved in the active rental relation within EJAR.

Key Operations for Electricity Liability Transfer:

SEC provides the two main operations through which liability for electricity services is transferred:

Tenant Move-In (MI): This operation transfers the electricity service liability in SEC’s SAP IS-U system from the owner/lessor to the tenant based on a valid rental contract. When successful, SEC issues the new bills under the tenant’s name. The tenant is then considered the actual beneficiary liable for consumption charges and related invoices during the contract period.

Tenant Move-Out (MO): This operation transfers electricity service liability back from the tenant to the owner/lessor when a contract is expired or terminated. SEC issues a final electricity invoice to the tenant and then transfers the liability back to the owner/lessor.

In short, SEC provides the actual electricity service and the technical infrastructure (SAP IS-U) to manage billing and meters, while EJAR initiates the legal and procedural requests (Move-In/Move-Out) that dictate who is liable for that service.
