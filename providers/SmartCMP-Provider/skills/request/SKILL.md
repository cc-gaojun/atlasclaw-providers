---
name: "request"
description: "SmartCMP resource request. Create VM, provision cloud resources, deploy applications. Keywords: request, provision, deploy, create VM, apply resources, 申请资源, 创建虚拟机, 资源申请"
provider_type: "smartcmp"
instance_required: "true"
tool_list_services_name: "smartcmp_list_services"
tool_list_services_description: "List available service catalogs from SmartCMP. Use for: view available services, check what can be provisioned, list catalogs. 查看可申请的服务目录"
tool_list_services_entrypoint: "../shared/scripts/list_services.py"
tool_list_business_groups_name: "smartcmp_list_business_groups"
tool_list_business_groups_description: "List business groups for a catalog. Use when user needs to select business group."
tool_list_business_groups_entrypoint: "../shared/scripts/list_business_groups.py"
tool_list_resource_pools_name: "smartcmp_list_resource_pools"
tool_list_resource_pools_description: "List resource pools. Get resourceBundleId for request."
tool_list_resource_pools_entrypoint: "../shared/scripts/list_resource_pools.py"
tool_list_os_templates_name: "smartcmp_list_os_templates"
tool_list_os_templates_description: "List OS templates for VM provisioning."
tool_list_os_templates_entrypoint: "../shared/scripts/list_os_templates.py"
tool_submit_name: "smartcmp_submit_request"
tool_submit_description: "Submit resource request to SmartCMP. 提交资源申请"
tool_submit_entrypoint: "scripts/submit.py"
---

# request

SmartCMP resource provisioning request skill.

## Purpose

Submit cloud resource or application provisioning requests through SmartCMP platform with interactive parameter collection.

## Trigger Conditions

Use this skill when user intent is any of:
- Provision / deploy resources
- Create virtual machine / VM
- 创建虚拟机 / VM申请 / 申请虚拟机
- Request cloud resources
- 申请云资源 / 资源申请
- Deploy application
- 部署应用

| Intent | Keywords |
|--------|----------|
| Provision resources | "provision", "deploy", "create resources" |
| Create VM | "create VM", "create virtual machine", "new VM" |
| Request cloud resources | "request cloud", "need cloud resources" |
| Deploy application | "deploy app", "deploy application" |

## Scripts

**Data Collection Scripts** (in `../shared/scripts/`):

| Script | Description | Returns |
|--------|-------------|---------|
| `list_services.py` | List published service catalogs | `catalogId`, `sourceKey` |
| `list_components.py` | Get component type | `typeName` (nodeType), `osType` |
| `list_business_groups.py` | List business groups | `bgId` |
| `list_applications.py` | List applications | `applicationId` |
| `list_resource_pools.py` | List resource pools | `resourceBundleId`, `cloudEntryTypeId` |
| `list_os_templates.py` | List OS templates (VM) | `logicTemplateId` |
| `list_cloud_entry_types.py` | Get cloud entry types | `cloudEntryType` |
| `list_images.py` | List images (private cloud) | `imageId` |

**Submit Script** (in `scripts/`):

| Script | Description |
|--------|-------------|
| `submit.py` | Submit the assembled request |

## Environment Setup

### Option 1: Direct Cookie
```powershell
# PowerShell - CMP_URL auto-normalizes (adds /platform-api if missing)
$env:CMP_URL = "<your-cmp-host>"
$env:CMP_COOKIE = '<full cookie string>'
```

```bash
# Bash
export CMP_URL="<your-cmp-host>"
export CMP_COOKIE="<full cookie string>"
```

### Option 2: Auto-Login (Recommended)
Automatically obtains and caches cookies (30-minute TTL).

```powershell
# PowerShell
$env:CMP_URL = "<your-cmp-host>"
$env:CMP_USERNAME = "<username>"
$env:CMP_PASSWORD = "<password>"
$env:CMP_AUTH_URL = "<auth endpoint>"
```

```bash
# Bash
export CMP_URL="<your-cmp-host>"
export CMP_USERNAME="<username>"
export CMP_PASSWORD="<password>"
export CMP_AUTH_URL="<auth endpoint>"
```

## Workflow

### Step 1: List Available Services

```bash
python ../shared/scripts/list_services.py
```

Parse `##CATALOG_META_START## ... ##CATALOG_META_END##` to get `id` (catalogId) and `sourceKey`.

### Step 2: Get Component Type

```bash
python ../shared/scripts/list_components.py <sourceKey>
```

Parse `##COMPONENT_META_START## ... ##COMPONENT_META_END##` to get `typeName` (used as nodeType).

**Determine osType:**
- If `typeName` contains "windows" → osType = "Windows"
- Otherwise → osType = "Linux"

### Step 3: List Business Groups

```bash
python ../shared/scripts/list_business_groups.py <catalogId>
```

Let user select business group → get `bgId`.

### Step 4: List Resource Pools

```bash
python ../shared/scripts/list_resource_pools.py <bgId> <sourceKey> <nodeType>
```

Parse `##RESOURCE_POOL_META_START## ... ##RESOURCE_POOL_META_END##` to get `resourceBundleId` and `cloudEntryTypeId`.

### Step 5: List OS Templates (VM Only)

```bash
python ../shared/scripts/list_os_templates.py <osType> <resourceBundleId>
```

### Step 6: Collect User Parameters

Interactive collection:
- Instance name
- CPU, Memory, Storage
- Network configuration
- Tags (optional)

### Step 7: Build Request Body

```json
{
  "catalogId": "<from step 1>",
  "businessGroupId": "<from step 3>",
  "name": "<user provided>",
  "description": "<user provided>",
  "resourceSpecs": {
    "<nodeType>": {
      "quantity": 1,
      "resourceBundleId": "<from step 4>",
      "cpu": 2,
      "memory": 4096,
      ...
    }
  }
}
```

**Show to user for confirmation before submit.**

### Step 8: Submit Request

```bash
python scripts/submit.py --file request_body.json
```

Return Request ID and State to user.

## Data Flow

```
list_services.py → catalogId, sourceKey
        ↓
list_components.py → nodeType, osType
        ↓
list_business_groups.py → bgId
        ↓
list_resource_pools.py → resourceBundleId, cloudEntryTypeId
        ↓
list_os_templates.py → logicTemplateId
        ↓
[Collect user parameters]
        ↓
[Build JSON body]
        ↓
submit.py → Request ID, State
```

## Critical Rules

> **NEVER create temp files** — no `.py`, `.txt`, `.json`. Your context IS your memory.

> **NEVER redirect output** — no `>`, `>>`, `2>&1`. Run scripts directly, read stdout.

> **NEVER flatten request body** — VM fields MUST be inside `resourceSpecs[]` array.

> **NEVER pass JSON as command-line string** in PowerShell — use `--file`.

## Error Handling

| Error | Resolution |
|-------|------------|
| `401` / Token expired | Refresh `CMP_COOKIE` environment variable |
| `[ERROR]` output | Report to user immediately; do NOT self-debug |
| Missing required fields | Check PARAMS.md for field requirements |

## References

- [WORKFLOW.md](references/WORKFLOW.md) — Detailed step-by-step workflow
- [PARAMS.md](references/PARAMS.md) — Parameter placement rules
- [EXAMPLES.md](references/EXAMPLES.md) — Request body examples
