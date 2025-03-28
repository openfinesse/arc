# Resume Point Construction

You will be provided a bullet point from a resume. You are to provide a structured output in YAML. The output will serve as a modular structure that a subsequent LLM will use to customize resumes points based on a given job description. What makes this unique from regular AI resume customizers is that the structure provides a template and implicit rules.

Things the structure should include are: structured modular base sentence(s), and variations to fill out that modular structure. These variations should not be too specific. They should maintain some context so the an agent does not lose perspective of the sentence flow when working on a specific option. The variations can also include adjacent terms or phrases that are not explicitly mentioned but might enhance the ability of match with job requirements.

## Example 1

### Input

"Administered Linux and Windows servers in environments with Hyper-V virtualization; configured server roles (Active Directory, DNS, DHCP, Group Policy) and set up Azure infrastructure (VMs, networking, storage), reducing unplanned system downtime by 20%"

### Output

base_sentences:
  - "{configured_1} {systems} in environments with {virtualization}; {configured_2} {server_components}, reducing unplanned system downtime by 20%"
  - "{configured_1} {systems} in environments with {virtualization}; {configured_2} {server_components} and set up {azure}, reducing unplanned system downtime by 20%"
  - "Achieved a 20% reduction in unplanned system downtime by {configured_2} {server_components} in a {virtualization} environment, and setting up {azure}"
  - "Achieved a 20% reduction in unplanned system downtime by {configured_2} {server_components} in a {virtualization} environment"
  - "{configured_1} {azure}, reducing unplanned system downtime by 20%"
variations:
  systems:
    - "Linux and Windows servers"
    - "Windows Server infrastructure"
    - "multi-platform server environments"
    - "Linux servers"
    - "Windows servers"
  virtualization:
    - "Hyper-V virtualization"
    - "virtual infrastructure"
    - "hybrid cloud infrastructure"
    - "KVM virtualization"
    - "Proxmox virtualization"
    - "KVM"
    - "Proxmox"
    - "Hyper-V"
  configured_1:
    - "Configured"
    - "Implemented and maintained"
    - "Deployed and managed"
    - "Administered"
    - "Deployed"
  configured_2:
    - "configured"
    - "configuring"
    - "implemented and maintained"
    - "deployed and managed"
    - "administering"
    - "deploying"
    - "administered"
  server_components:
    - "server roles (Active Directory, DNS, DHCP, Group Policy)"
    - "critical infrastructure services"
    - "Active Directory, DNS, DHCP, and Group Policy"
    - "Active Directory and Group Policy"
    - "DNS and DHCP"
    - "Active Directory, DNS, and DHCP"
  azure:
    - "Azure infrastructure (VMs, networking, storage)"
    - "Azure VMs, networking, and storage"
    - "Azure infrastructure"
    - "Azure virtual machines"
    - "Azure networking"
    - "Azure storage"
