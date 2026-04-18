# ADR-0005: RBAC Strategy

> **Status**: Accepted
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

MVP có 2 role: **Landlord** và **Tenant**. Roadmap đã xác định:
- v1.x: thêm **Manager** (quản lý một số Property, quyền hạn chế)
- v2.x: thêm **Investor** (xem báo cáo, không thao tác), **Technician**

Manager là role phức tạp — không phải "Landlord bị giới hạn" mà là
role độc lập với permission set riêng. Ví dụ:
- Manager có thể tạo Invoice nhưng không thể xóa Property
- Manager chỉ quản lý Property được assign, không thấy Property khác
- Investor chỉ có quyền đọc báo cáo tài chính

Nếu dùng role-based thuần (check `user.role == "landlord"`), thêm
Manager ở v1.x sẽ phải sửa business logic ở nhiều nơi — rủi ro cao,
khó test, không scale.

---

## Decision

Dùng **Permission-based RBAC** với role là tập hợp permissions.

### Mô hình

```
User → Role → [Permission, Permission, ...]
```

Permission là string dạng `resource:action`:

```
property:read       property:create     property:delete
room:read           room:create         room:update         room:archive
tenant:read         tenant:create       tenant:archive
lease:read          lease:create        lease:terminate
invoice:read        invoice:create      invoice:void
payment:read        payment:create      payment:delete
service:read        service:create      service:update
meter_reading:read  meter_reading:create meter_reading:update
```

### Permission sets theo role

**Landlord** — toàn quyền trên Property của mình:
```python
LANDLORD_PERMISSIONS = {
    "property:read", "property:create", "property:update", "property:delete",
    "room:read", "room:create", "room:update", "room:archive",
    "tenant:read", "tenant:create", "tenant:update", "tenant:archive",
    "lease:read", "lease:create", "lease:update", "lease:terminate",
    "invoice:read", "invoice:create", "invoice:void",
    "payment:read", "payment:create", "payment:delete",
    "service:read", "service:create", "service:update", "service:toggle",
    "meter_reading:read", "meter_reading:create", "meter_reading:update",
    "occupant:read", "occupant:create", "occupant:update", "occupant:delete",
}
```

**Tenant** — chỉ đọc data liên quan đến mình:
```python
TENANT_PERMISSIONS = {
    "invoice:read",      # Chỉ Invoice của mình
    "payment:read",      # Chỉ Payment của mình
    "lease:read",        # Chỉ Lease của mình
    "room:read",         # Chỉ Room của mình
}
```

**Manager** *(v1.x — define trước, chưa implement)*:
```python
MANAGER_PERMISSIONS = {
    "property:read",
    "room:read", "room:create", "room:update",
    "tenant:read", "tenant:create", "tenant:update",
    "lease:read", "lease:create",
    "invoice:read", "invoice:create",
    "payment:read", "payment:create",
    "service:read",
    "meter_reading:read", "meter_reading:create", "meter_reading:update",
    "occupant:read", "occupant:create", "occupant:update",
    # Không có: property:delete, property:create, service:create,
    #           invoice:void, payment:delete, lease:terminate
}
```

**Investor** *(v2.x — chỉ đọc báo cáo)*:
```python
INVESTOR_PERMISSIONS = {
    "property:read",
    "invoice:read",
    "payment:read",
    # Không có quyền write bất kỳ thứ gì
}
```

---

## Implementation

### 1. Database schema

Lưu role ở `users` table, permissions lưu **in-code** (không lưu DB):

```sql
-- users table
role  VARCHAR(20)  NOT NULL  -- 'landlord' | 'tenant' | 'manager' | 'investor'
```

**Lý do không lưu permissions vào DB**: Permission set thay đổi theo
code release, không phải theo user request. Lưu DB tạo ra nguy cơ
permission drift (DB và code không đồng bộ). Role → permissions mapping
là static config, quản lý trong code.

### 2. Permission check — FastAPI dependency

```python
# app/core/permissions.py

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "landlord": LANDLORD_PERMISSIONS,
    "tenant":   TENANT_PERMISSIONS,
    # v1.x:
    # "manager": MANAGER_PERMISSIONS,
}

def require_permission(permission: str):
    """FastAPI dependency — inject vào route."""
    def dependency(current_user: User = Depends(get_current_user)):
        allowed = ROLE_PERMISSIONS.get(current_user.role, set())
        if permission not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}"
            )
        return current_user
    return dependency
```

**Dùng trong route:**
```python
@router.post("/invoices")
def create_invoice(
    _: User = Depends(require_permission("invoice:create")),
    ...
):
    ...
```

### 3. Resource ownership check — tách khỏi permission

Permission check chỉ xác nhận "role này có quyền làm action này không".
Ownership check xác nhận "entity này có thuộc về user này không" —
xử lý ở **service layer**, không phải middleware:

```python
# app/services/invoice_service.py

async def get_invoice(invoice_id: UUID, current_user: User) -> Invoice:
    invoice = await invoice_repo.get(invoice_id)

    if current_user.role == "landlord":
        # Kiểm tra invoice thuộc property của landlord này
        if invoice.lease.room.property.landlord_id != current_user.id:
            raise HTTPException(404)  # 404, không phải 403 — không tiết lộ existence

    elif current_user.role == "tenant":
        # Kiểm tra invoice thuộc lease của tenant này
        if invoice.lease.tenant.user_id != current_user.id:
            raise HTTPException(404)

    return invoice
```

**Tại sao 404 thay vì 403?** 403 tiết lộ rằng resource tồn tại.
Tenant không nên biết Invoice của phòng khác có tồn tại hay không.

### 4. MVP: 1 user = 1 role

Multi-role (Landlord + Tenant cùng account) là open question từ Phase 2.
**Quyết định cho MVP**: 1 user = 1 role, enforce ở application layer.

Lý do: Use case thực tế (Landlord thuê nhà người khác) rất hiếm.
Implement multi-role phức tạp hơn nhiều và không có trong 63 user stories.
Defer sang v1.x nếu có demand thật.

---

## Ownership scope cho từng role

| Role | Scope thấy được |
|------|----------------|
| Landlord | Chỉ Property do mình tạo + mọi entity con |
| Tenant | Chỉ Room + Lease + Invoice + Payment của mình |
| Manager *(v1.x)* | Chỉ Property được assign bởi Landlord |
| Investor *(v2.x)* | Chỉ Property được assign bởi Landlord |

---

## Consequences

### Positive
- Thêm Manager (v1.x) chỉ cần: define `MANAGER_PERMISSIONS` + thêm
  ownership check trong service layer — không sửa business logic
- Permission rõ ràng, dễ audit ("ai có quyền làm gì")
- Test dễ: mock `current_user.role` → kiểm tra permission set

### Negative / Trade-offs
- Phức tạp hơn role-based thuần khi implement MVP
- Developer phải nhớ 2 tầng check: permission (middleware) +
  ownership (service layer)
- Permission string phải nhất quán — lỗi typo là silent bug

### Neutral
- Permissions lưu in-code → deploy mới để thay đổi quyền.
  Với scale solo dev + portfolio project, đây là acceptable trade-off.

---

## Mitigation

**Tránh typo permission string**: Define permissions là constants:
```python
class Permission:
    INVOICE_CREATE = "invoice:create"
    INVOICE_READ   = "invoice:read"
    INVOICE_VOID   = "invoice:void"
    # ...

# Dùng:
Depends(require_permission(Permission.INVOICE_CREATE))
```

**Test coverage bắt buộc cho permission**:
- Mỗi protected endpoint phải có test case: unauthenticated (401),
  wrong role (403), correct role (2xx)
- Test ownership: entity của người khác → 404

---

## References

- Phase 2 Summary — Section 5: ADR-0005
- Phase 2 Summary — User & Auth decisions (Nhóm 1)
- OWASP: Broken Access Control — https://owasp.org/Top10/A01_2021-Broken_Access_Control/
- FastAPI dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/
